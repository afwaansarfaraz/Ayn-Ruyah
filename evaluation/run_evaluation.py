"""Complete trained-model evaluation and verification pipeline for RetinaLens AI.

Executes genuine inference on the independent 30-image clinical benchmark dataset,
computes Quadratic Weighted Kappa (QWK), confusion matrices, per-class metrics,
and saves visualization charts and Grad-CAM saliency heatmaps.
"""

from __future__ import annotations

import base64
import csv
from datetime import datetime
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from filelock import FileLock

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from src.core.config import AppConfig
from src.core.constants import GRADE_LABELS, NUM_CLASSES
from src.models.loader import load_model
from src.services.diagnostic_service import DiagnosticService
from src.services.gradcam import GradCAMService
from src.services.image_validator import RetinalImageValidator
from src.services.preprocessing import RetinalPreprocessor

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("model_evaluation")

CLASS_NAMES = [
    "No DR (Grade 0)",
    "Mild NPDR (Grade 1)",
    "Moderate NPDR (Grade 2)",
    "Severe NPDR (Grade 3)",
    "Proliferative DR (Grade 4)",
]

SHORT_CLASSES = ["Grade 0", "Grade 1", "Grade 2", "Grade 3", "Grade 4"]


def main():
    logger.info("Initializing RetinaLens AI Model Evaluation Suite...")

    config = AppConfig(secret_key=os.getenv("SECRET_KEY", "eval-cli-mode-secret-key-32charsmin!"))
    eval_dir = PROJECT_ROOT / "data" / "evaluation_dataset"
    results_dir = PROJECT_ROOT / "evaluation" / "results"
    gradcam_dir = results_dir / "gradcam"

    # Stage heatmaps, metrics, and predictions in temporary directory
    staging_temp = tempfile.TemporaryDirectory()
    staging_dir = Path(staging_temp.name)
    staged_results_dir = staging_dir / "results"
    staged_gradcam_dir = staged_results_dir / "gradcam"
    staged_results_dir.mkdir(parents=True, exist_ok=True)
    staged_gradcam_dir.mkdir(parents=True, exist_ok=True)

    try:

        # 1. Load trained production model
        logger.info("Loading trained EfficientNet-B4 from %s", config.weights_path)
        model = load_model(config)
        if model is None:
            raise RuntimeError("FATAL: Checkpoint weights/best.pt could not be loaded!")

        validator = RetinalImageValidator()
        preprocessor = RetinalPreprocessor(config)
        gradcam_svc = GradCAMService(model)
        diag_svc = DiagnosticService(
            model=model,
            validator=validator,
            preprocessor=preprocessor,
            gradcam=gradcam_svc,
        )

        # 2. Load Evaluation Ground Truth Manifest
        manifest_path = eval_dir / "ground_truth_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        logger.info("Loaded %d benchmark images from manifest.", len(manifest))

        # 3. Execute Inference on Every Evaluation Image
        prediction_records = []
        y_true = []
        y_pred = []
        latencies = []
        representative_samples = {}  # Store one representative per grade for gallery

        for idx, entry in enumerate(manifest, start=1):
            image_path = eval_dir / "images" / entry["filename"]
            if not image_path.exists():
                raise FileNotFoundError(f"Evaluation image missing: {image_path}")

            image_bytes = image_path.read_bytes()
            true_grade = int(entry["ground_truth_grade"])

            t0 = time.perf_counter()
            result = diag_svc.analyze_image_bytes(image_bytes)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(latency_ms)

            pred_grade = result.grade
            confidence = result.confidence
            correct = (pred_grade == true_grade)

            y_true.append(true_grade)
            y_pred.append(pred_grade)

            # Save Grad-CAM image into staged directory
            gradcam_filename = f"{entry['image_id']}_gradcam.png"
            gradcam_save_path = staged_gradcam_dir / gradcam_filename

            if result.heatmap and "base64," in result.heatmap:
                b64_data = result.heatmap.split("base64,")[1]
                gradcam_bytes = base64.b64decode(b64_data)
                gradcam_save_path.write_bytes(gradcam_bytes)
            else:
                raise ValueError(
                    f"Grad-CAM save failure: expected valid base64 data URI marker for image {entry['image_id']}, "
                    f"got: {result.heatmap!r}"
                )

            if true_grade not in representative_samples:
                representative_samples[true_grade] = {
                    "orig_path": image_path,
                    "gradcam_path": gradcam_save_path,
                    "entry": entry,
                    "result": result,
                }

            record = {
                "index": idx,
                "image_id": entry["image_id"],
                "filename": entry["filename"],
                "ground_truth_grade": true_grade,
                "ground_truth_label": entry["ground_truth_label"],
                "predicted_grade": pred_grade,
                "predicted_label": result.result,
                "confidence_percent": round(confidence, 2),
                "correct": correct,
                "latency_ms": round(latency_ms, 1),
                "prob_grade0": result.probabilities.get(GRADE_LABELS[0], 0.0),
                "prob_grade1": result.probabilities.get(GRADE_LABELS[1], 0.0),
                "prob_grade2": result.probabilities.get(GRADE_LABELS[2], 0.0),
                "prob_grade3": result.probabilities.get(GRADE_LABELS[3], 0.0),
                "prob_grade4": result.probabilities.get(GRADE_LABELS[4], 0.0),
                "dataset_source": entry["dataset_source"],
            }
            prediction_records.append(record)

            logger.info(
                "[%02d/%02d] %s: True=%s | Pred=%s (%.1f%%) | %s (%.0f ms)",
                idx,
                len(manifest),
                entry["filename"],
                GRADE_LABELS[true_grade],
                result.result,
                confidence,
                "CORRECT" if correct else "MISCLASSIFIED",
                latency_ms,
            )

        # 4. Compute Comprehensive Evaluation Metrics
        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)

        qwk = cohen_kappa_score(y_true_arr, y_pred_arr, weights="quadratic")
        unweighted_kappa = cohen_kappa_score(y_true_arr, y_pred_arr)
        overall_accuracy = accuracy_score(y_true_arr, y_pred_arr)

        macro_precision = precision_score(y_true_arr, y_pred_arr, average="macro", zero_division=0)
        macro_recall = recall_score(y_true_arr, y_pred_arr, average="macro", zero_division=0)
        macro_f1 = f1_score(y_true_arr, y_pred_arr, average="macro", zero_division=0)

        weighted_precision = precision_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0)
        weighted_recall = recall_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0)
        weighted_f1 = f1_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0)

        # Per-Class Precision, Recall, F1, Support
        per_class_p = precision_score(y_true_arr, y_pred_arr, average=None, zero_division=0, labels=range(5))
        per_class_r = recall_score(y_true_arr, y_pred_arr, average=None, zero_division=0, labels=range(5))
        per_class_f = f1_score(y_true_arr, y_pred_arr, average=None, zero_division=0, labels=range(5))

        per_class_metrics = {}
        for g in range(5):
            support = int((y_true_arr == g).sum())
            per_class_metrics[f"grade_{g}"] = {
                "grade": g,
                "label": GRADE_LABELS[g],
                "precision": round(float(per_class_p[g]), 4),
                "recall": round(float(per_class_r[g]), 4),
                "f1_score": round(float(per_class_f[g]), 4),
                "support": support,
            }

        # Clinical Referral Metrics (Referable DR = Grade >= 2)
        ref_true = (y_true_arr >= 2).astype(int)
        ref_pred = (y_pred_arr >= 2).astype(int)
        ref_acc = accuracy_score(ref_true, ref_pred)
        ref_recall = recall_score(ref_true, ref_pred, zero_division=0)       # Clinical Sensitivity
        ref_precision = precision_score(ref_true, ref_pred, zero_division=0) # Positive Predictive Value
        ref_f1 = f1_score(ref_true, ref_pred, zero_division=0)

        cm_raw = confusion_matrix(y_true_arr, y_pred_arr, labels=range(5))
        cm_norm = confusion_matrix(y_true_arr, y_pred_arr, labels=range(5), normalize="true")

        metrics_summary = {
            "evaluation_dataset": "MICCAI DDR Test Benchmark (Independent Held-Out External)",
            "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
            "total_images": len(manifest),
            "class_distribution": {f"Grade_{g}": int((y_true_arr == g).sum()) for g in range(5)},
            "quadratic_weighted_kappa": round(float(qwk), 4),
            "unweighted_kappa": round(float(unweighted_kappa), 4),
            "overall_accuracy": round(float(overall_accuracy), 4),
            "macro_precision": round(float(macro_precision), 4),
            "macro_recall": round(float(macro_recall), 4),
            "macro_f1": round(float(macro_f1), 4),
            "weighted_f1": round(float(weighted_f1), 4),
            "clinical_referable_dr_metrics": {
                "referable_definition": "Grade >= 2 (Moderate, Severe, or Proliferative DR)",
                "accuracy": round(float(ref_acc), 4),
                "sensitivity": round(float(ref_recall), 4),
                "precision": round(float(ref_precision), 4),
                "f1_score": round(float(ref_f1), 4),
            },
            "per_class_metrics": per_class_metrics,
            "latency_ms": {
                "mean": round(float(np.mean(latencies)), 1),
                "median": round(float(np.median(latencies)), 1),
                "min": round(float(np.min(latencies)), 1),
                "max": round(float(np.max(latencies)), 1),
            },
            "confusion_matrix_raw": cm_raw.tolist(),
            "confusion_matrix_normalized": np.round(cm_norm, 4).tolist(),
        }

        # Save metrics JSON into staged directory
        with open(staged_results_dir / "evaluation_metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics_summary, f, indent=2)

        # Save predictions CSV & JSON into staged directory
        with open(staged_results_dir / "predictions_table.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(prediction_records[0].keys()))
            writer.writeheader()
            writer.writerows(prediction_records)

        with open(staged_results_dir / "predictions_table.json", "w", encoding="utf-8") as f:
            json.dump(prediction_records, f, indent=2)

        logger.info("Saved metrics and predictions table to staged directory.")

        # 5. Generate Figures into staged directory
        generate_figures(
            results_dir=staged_results_dir,
            cm_raw=cm_raw,
            cm_norm=cm_norm,
            per_class_metrics=per_class_metrics,
            qwk=qwk,
            acc=overall_accuracy,
            macro_f1=macro_f1,
            representative_samples=representative_samples,
        )

        # 6. Complete Versioned Publication and Atomic Switch Protected by Interprocess FileLock
        results_dir.mkdir(parents=True, exist_ok=True)
        versions_dir = results_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        version_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        version_dir = versions_dir / version_id

        lock_path = results_dir / ".publish.lock"
        with FileLock(str(lock_path), timeout=60):
            # Publish complete versioned artifact set (metrics, predictions, heatmaps, figures)
            shutil.copytree(staged_results_dir, version_dir)

            # Store relative version path for portability across environments
            rel_version_path = f"versions/{version_id}"
            pointer_data = {
                "active_version": version_id,
                "version_path": rel_version_path,
                "published_at": datetime.utcnow().isoformat() + "Z",
                "metrics": metrics_summary,
            }
            pointer_tmp = results_dir / f".active_version_{version_id}.tmp"
            with open(pointer_tmp, "w", encoding="utf-8") as f:
                json.dump(pointer_data, f, indent=2)
            os.replace(pointer_tmp, results_dir / "active_version.json")

            # Atomically publish individual files in results_dir (preserving unrelated files)
            for item in version_dir.iterdir():
                if item.is_file():
                    tmp_target = results_dir / f".{item.name}.tmp"
                    shutil.copy2(item, tmp_target)
                    os.replace(tmp_target, results_dir / item.name)

            # Atomically switch gradcam directory
            staged_vc_gradcam = version_dir / "gradcam"
            if staged_vc_gradcam.exists():
                gradcam_tmp = results_dir / f".gradcam_{version_id}_tmp"
                gradcam_old = results_dir / f".gradcam_{version_id}_old"
                shutil.copytree(staged_vc_gradcam, gradcam_tmp)
                if gradcam_dir.exists():
                    gradcam_dir.rename(gradcam_old)
                gradcam_tmp.rename(gradcam_dir)
                if gradcam_old.exists():
                    shutil.rmtree(gradcam_old, ignore_errors=True)

        logger.info("Published complete versioned evaluation set: %s (%s)", version_id, version_dir)
        logger.info("Evaluation complete! QWK: %.4f, Accuracy: %.2f%%, Macro F1: %.4f", qwk, overall_accuracy * 100.0, macro_f1)
        return metrics_summary
    finally:
        staging_temp.cleanup()


def generate_figures(results_dir, cm_raw, cm_norm, per_class_metrics, qwk, acc, macro_f1, representative_samples):
    # 1. Raw Confusion Matrix Heatmap
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    im = ax.imshow(cm_raw, cmap="Blues", interpolation="nearest")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=10)

    ax.set_xticks(range(5))
    ax.set_yticks(range(5))
    ax.set_xticklabels(SHORT_CLASSES, fontsize=10, fontweight="bold")
    ax.set_yticklabels(SHORT_CLASSES, fontsize=10, fontweight="bold")
    ax.set_xlabel("Predicted DR Grade", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Ground Truth DR Grade", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_title(f"Confusion Matrix (Raw Counts)\nQWK: {qwk:.4f} | Overall Accuracy: {acc*100:.1f}%", fontsize=13, fontweight="bold", pad=12)

    # Annotate counts
    thresh = cm_raw.max() / 2.0
    for i in range(5):
        for j in range(5):
            val = cm_raw[i, j]
            color = "white" if val > thresh else "black"
            ax.text(j, i, str(val), ha="center", va="center", color=color, fontsize=12, fontweight="bold")

    plt.tight_layout()
    plt.savefig(results_dir / "confusion_matrix_raw.png", dpi=250)
    plt.close()

    # 2. Normalized Confusion Matrix Heatmap
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    im = ax.imshow(cm_norm, cmap="Purples", interpolation="nearest")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=10)

    ax.set_xticks(range(5))
    ax.set_yticks(range(5))
    ax.set_xticklabels(SHORT_CLASSES, fontsize=10, fontweight="bold")
    ax.set_yticklabels(SHORT_CLASSES, fontsize=10, fontweight="bold")
    ax.set_xlabel("Predicted DR Grade", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Ground Truth DR Grade", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_title("Normalized Confusion Matrix (Row-Normalized / Recall)", fontsize=13, fontweight="bold", pad=12)

    # Annotate percentages
    thresh_norm = cm_norm.max() / 2.0
    for i in range(5):
        for j in range(5):
            val = cm_norm[i, j]
            color = "white" if val > thresh_norm else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=11, fontweight="bold")

    plt.tight_layout()
    plt.savefig(results_dir / "confusion_matrix_normalized.png", dpi=250)
    plt.close()

    # 3. Per-Class Metrics Bar Chart
    grades = [f"Grade {g}" for g in range(5)]
    precisions = [per_class_metrics[f"grade_{g}"]["precision"] for g in range(5)]
    recalls = [per_class_metrics[f"grade_{g}"]["recall"] for g in range(5)]
    f1s = [per_class_metrics[f"grade_{g}"]["f1_score"] for g in range(5)]

    x = np.arange(len(grades))
    width = 0.25

    plt.figure(figsize=(10, 5.5))
    plt.bar(x - width, precisions, width, label="Precision", color="#3b82f6", alpha=0.9)
    plt.bar(x, recalls, width, label="Recall (Sensitivity)", color="#10b981", alpha=0.9)
    plt.bar(x + width, f1s, width, label="F1-Score", color="#8b5cf6", alpha=0.9)

    plt.xlabel("Diabetic Retinopathy Grade", fontsize=11, fontweight="bold")
    plt.ylabel("Score (0.0 to 1.0)", fontsize=11, fontweight="bold")
    plt.title("Per-Class Performance Breakdown across 5 DR Severity Grades", fontsize=13, fontweight="bold", pad=12)
    plt.xticks(x, [f"{GRADE_LABELS[g]}\n(Grade {g})" for g in range(5)], fontsize=9)
    plt.ylim(0, 1.1)
    plt.legend(frameon=True, facecolor="#f8fafc")
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(results_dir / "per_class_metrics_bar.png", dpi=250)
    plt.close()

    # 4. Grad-CAM Representative Gallery across all 5 grades
    fig, axes = plt.subplots(5, 2, figsize=(10, 18))
    for g in range(5):
        sample = representative_samples.get(g)
        if sample:
            orig = Image.open(sample["orig_path"]).convert("RGB")
            gradcam = Image.open(sample["gradcam_path"]).convert("RGB")
            res = sample["result"]

            axes[g, 0].imshow(orig)
            axes[g, 0].set_title(f"True: {sample['entry']['ground_truth_label']} (Grade {g})\nFile: {sample['entry']['filename']}", fontsize=10, fontweight="bold")
            axes[g, 0].axis("off")

            axes[g, 1].imshow(gradcam)
            match_str = "MATCH" if res.grade == g else f"MISCLASSIFIED -> Grade {res.grade}"
            axes[g, 1].set_title(f"Grad-CAM Heatmap Overlay\nPredicted: {res.result} ({res.confidence:.1f}%) [{match_str}]", fontsize=10, fontweight="bold", color="#10b981" if res.grade == g else "#ef4444")
            axes[g, 1].axis("off")

    plt.suptitle("RetinaLens AI Grad-CAM Saliency Maps Across All 5 DR Grades\n(Layer: conv_head, 1792 channels)", fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout()
    plt.savefig(results_dir / "gradcam_gallery.png", dpi=200)
    plt.close()


if __name__ == "__main__":
    main()
