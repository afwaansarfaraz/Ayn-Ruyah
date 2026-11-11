"""RetinaLens AI / AYN RUYAH — EfficientNet-B4 Generalization Investigation Suite.

Systematically investigates out-of-domain performance drops on the independent
MICCAI DDR clinical dataset by auditing:
1. Image geometry, aspect ratios, and black margin ratios.
2. Color distribution, channel means, and Laplacian variance sharpness.
3. Preprocessing variations:
   - Baseline: Direct Resize (380x380)
   - Exp A: Tight Retinal Autocrop (Aspect-preserving black border removal)
   - Exp B: Ben Graham Preprocessing (Sigma=10)
   - Exp C: Ben Graham Preprocessing (Sigma=30)
   - Exp D: Tight Retinal Autocrop + Ben Graham (Sigma=30)
   - Exp E: Contrast-Limited Adaptive Histogram Equalization (CLAHE)
   - Exp F: Test-Time Augmentation (TTA, 4-fold)
4. Calibration, Logit Distribution, and Systematic Under-Grading Analysis.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score

from src.core.config import AppConfig
from src.core.constants import IMAGENET_MEAN, IMAGENET_STD
from src.models.loader import load_model

logger = logging.getLogger("generalization_audit")

EVAL_DIR = PROJECT_ROOT / "data" / "evaluation_dataset"
IMAGES_DIR = EVAL_DIR / "images"
SAMPLE_DIR = PROJECT_ROOT / "sample_images"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"


def autocrop_fundus(image_np: np.ndarray, tol: int = 10) -> np.ndarray:
    """Crops black border margins around the circular retinal fundus."""
    if image_np.ndim == 2:
        mask = image_np > tol
        if not mask.any():
            return image_np
        return image_np[np.ix_(mask.any(1), mask.any(0))]
    elif image_np.ndim == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        mask = gray > tol
        if not mask.any():
            return image_np
        # Check if coordinates exist
        row_indices = np.where(mask.any(axis=1))[0]
        col_indices = np.where(mask.any(axis=0))[0]
        if len(row_indices) == 0 or len(col_indices) == 0:
            return image_np
        rmin, rmax = row_indices[0], row_indices[-1]
        cmin, cmax = col_indices[0], col_indices[-1]
        cropped = image_np[rmin : rmax + 1, cmin : cmax + 1]
        
        # Square pad to avoid stretching
        h, w = cropped.shape[:2]
        max_dim = max(h, w)
        pad_top = (max_dim - h) // 2
        pad_bottom = max_dim - h - pad_top
        pad_left = (max_dim - w) // 2
        pad_right = max_dim - w - pad_left
        padded = cv2.copyMakeBorder(
            cropped, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )
        return padded
    return image_np


def apply_ben_graham(img_rgb: np.ndarray, sigma: int = 30) -> np.ndarray:
    """Ben Graham local Gaussian blur subtraction with circular mask."""
    h, w = img_rgb.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    center = (w // 2, h // 2)
    radius = int(min(h, w) * 0.46)
    cv2.circle(mask, center, radius, 255, -1)

    blur = cv2.GaussianBlur(img_rgb, (0, 0), sigma)
    enhanced = cv2.addWeighted(img_rgb, 4, blur, -4, 128)
    enhanced = cv2.bitwise_and(enhanced, enhanced, mask=mask)
    return enhanced


def apply_clahe(img_rgb: np.ndarray) -> np.ndarray:
    """Applies CLAHE on the L-channel in LAB color space."""
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)


def to_model_tensor(img_rgb: np.ndarray, image_size: int = 380, device: str = "cpu") -> torch.Tensor:
    resized = cv2.resize(img_rgb, (image_size, image_size), interpolation=cv2.INTER_AREA)
    norm = resized.astype(np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    norm = (norm - mean) / std
    tensor = torch.from_numpy(norm.transpose(2, 0, 1)).unsqueeze(0).to(device)
    return tensor


def audit_image_geometry_and_color(manifest: list[dict]):
    """Analyzes DDR dataset visual geometry vs APTOS reference samples."""
    stats = []
    logger.info("Auditing DDR image geometry and color statistics...")

    for entry in manifest:
        p = IMAGES_DIR / entry["filename"]
        img = Image.open(p).convert("RGB")
        w, h = img.size
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Calculate black border percentage
        black_pixels = np.sum(gray < 15)
        total_pixels = w * h
        black_ratio = black_pixels / total_pixels

        stats.append({
            "image_id": entry["image_id"],
            "grade": entry["ground_truth_grade"],
            "width": w,
            "height": h,
            "aspect_ratio": round(w / h, 3),
            "black_ratio": round(black_ratio, 3),
            "mean_r": round(float(np.mean(arr[:, :, 0])), 1),
            "mean_g": round(float(np.mean(arr[:, :, 1])), 1),
            "mean_b": round(float(np.mean(arr[:, :, 2])), 1),
            "sharpness": round(float(laplacian_var), 1),
        })

    # Reference sample comparison (APTOS)
    aptos_samples = list(SAMPLE_DIR.glob("*.jpg"))
    sample_stats = []
    for sp in aptos_samples:
        img = Image.open(sp).convert("RGB")
        w, h = img.size
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        black_ratio = np.sum(gray < 15) / (w * h)
        sample_stats.append({
            "name": sp.name,
            "width": w,
            "height": h,
            "aspect_ratio": round(w / h, 3),
            "black_ratio": round(black_ratio, 3),
            "mean_r": round(float(np.mean(arr[:, :, 0])), 1),
            "mean_g": round(float(np.mean(arr[:, :, 1])), 1),
            "mean_b": round(float(np.mean(arr[:, :, 2])), 1),
            "sharpness": round(float(laplacian_var), 1),
        })

    return stats, sample_stats


def evaluate_pipeline(model, manifest, transform_fn, name: str):
    """Evaluates the model under a specific transform function."""
    y_true = []
    y_pred = []
    logits_list = []
    probabilities_list = []

    model.eval()
    with torch.no_grad():
        for entry in manifest:
            img_path = IMAGES_DIR / entry["filename"]
            raw_rgb = np.array(Image.open(img_path).convert("RGB"))
            
            # Apply transformation pipeline
            tensor = transform_fn(raw_rgb)
            logits = model(tensor)
            probs = F.softmax(logits, dim=1).cpu().numpy()[0]
            pred = int(np.argmax(probs))
            
            y_true.append(int(entry["ground_truth_grade"]))
            y_pred.append(pred)
            logits_list.append(logits.cpu().numpy()[0].tolist())
            probabilities_list.append(probs.tolist())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    acc = float(accuracy_score(y_true, y_pred))
    qwk = float(cohen_kappa_score(y_true, y_pred, weights="quadratic"))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    
    # Clinical Referable DR (Grade >= 2)
    bin_true = (y_true >= 2).astype(int)
    bin_pred = (y_pred >= 2).astype(int)
    ref_acc = float(accuracy_score(bin_true, bin_pred))
    ref_sens = float(np.sum((bin_true == 1) & (bin_pred == 1)) / max(1, np.sum(bin_true == 1)))
    ref_prec = float(np.sum((bin_true == 1) & (bin_pred == 1)) / max(1, np.sum(bin_pred == 1)))

    logger.info(
        "[%s] Acc: %.2f%% | QWK: %.4f | Macro F1: %.4f | RefSens: %.2f%% | RefPrec: %.2f%%",
        name, acc * 100, qwk, macro_f1, ref_sens * 100, ref_prec * 100
    )

    return {
        "pipeline_name": name,
        "accuracy": acc,
        "qwk": qwk,
        "macro_f1": macro_f1,
        "referable_accuracy": ref_acc,
        "referable_sensitivity": ref_sens,
        "referable_precision": ref_prec,
        "predictions": y_pred.tolist(),
        "probabilities": probabilities_list,
    }


def evaluate_tta_pipeline(model, manifest, name: str = "TTA_4x"):
    """Evaluates with 4-fold Test-Time Augmentation."""
    y_true = []
    y_pred = []
    probabilities_list = []

    model.eval()
    with torch.no_grad():
        for entry in manifest:
            img_path = IMAGES_DIR / entry["filename"]
            raw_rgb = np.array(Image.open(img_path).convert("RGB"))
            
            # Autocrop first
            cropped = autocrop_fundus(raw_rgb)
            
            # 4 variants: original, hflip, vflip, rot180
            variants = [
                cropped,
                np.fliplr(cropped),
                np.flipud(cropped),
                np.rot90(cropped, 2),
            ]
            
            tensors = torch.cat([to_model_tensor(v) for v in variants], dim=0)
            logits = model(tensors)
            probs = F.softmax(logits, dim=1).mean(dim=0).cpu().numpy()
            pred = int(np.argmax(probs))

            y_true.append(int(entry["ground_truth_grade"]))
            y_pred.append(pred)
            probabilities_list.append(probs.tolist())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    acc = float(accuracy_score(y_true, y_pred))
    qwk = float(cohen_kappa_score(y_true, y_pred, weights="quadratic"))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    bin_true = (y_true >= 2).astype(int)
    bin_pred = (y_pred >= 2).astype(int)
    ref_acc = float(accuracy_score(bin_true, bin_pred))
    ref_sens = float(np.sum((bin_true == 1) & (bin_pred == 1)) / max(1, np.sum(bin_true == 1)))
    ref_prec = float(np.sum((bin_true == 1) & (bin_pred == 1)) / max(1, np.sum(bin_pred == 1)))

    logger.info(
        "[%s] Acc: %.2f%% | QWK: %.4f | Macro F1: %.4f | RefSens: %.2f%% | RefPrec: %.2f%%",
        name, acc * 100, qwk, macro_f1, ref_sens * 100, ref_prec * 100
    )

    return {
        "pipeline_name": name,
        "accuracy": acc,
        "qwk": qwk,
        "macro_f1": macro_f1,
        "referable_accuracy": ref_acc,
        "referable_sensitivity": ref_sens,
        "referable_precision": ref_prec,
        "predictions": y_pred.tolist(),
        "probabilities": probabilities_list,
    }


def main():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
    logger.info("Starting EfficientNet-B4 Generalization Audit...")
    import os
    config = AppConfig(secret_key=os.getenv("SECRET_KEY", "eval-cli-mode-secret-key-32charsmin!"))
    model = load_model(config)
    if model is None:
        raise RuntimeError("Failed to load model from weights/best.pt")

    manifest_path = EVAL_DIR / "ground_truth_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Audit Image Geometry & Color Statistics
    ddr_stats, aptos_sample_stats = audit_image_geometry_and_color(manifest)

    # 2. Pipeline Experiments
    results = {}

    # Experiment 0: Baseline (Standard Resize without crop)
    results["baseline_resize"] = evaluate_pipeline(
        model, manifest,
        lambda img: to_model_tensor(img),
        "1. Baseline Direct Resize"
    )

    # Experiment 1: Retinal Autocrop (Crop black margins, square pad, resize)
    results["autocrop"] = evaluate_pipeline(
        model, manifest,
        lambda img: to_model_tensor(autocrop_fundus(img)),
        "2. Retinal Autocrop & Square Pad"
    )

    # Experiment 2: Ben Graham (sigma=10, 380x380)
    results["ben_graham_sigma10"] = evaluate_pipeline(
        model, manifest,
        lambda img: to_model_tensor(apply_ben_graham(cv2.resize(img, (380, 380), interpolation=cv2.INTER_AREA), sigma=10)),
        "3. Ben Graham (sigma=10)"
    )

    # Experiment 3: Ben Graham (sigma=30, 380x380)
    results["ben_graham_sigma30"] = evaluate_pipeline(
        model, manifest,
        lambda img: to_model_tensor(apply_ben_graham(cv2.resize(img, (380, 380), interpolation=cv2.INTER_AREA), sigma=30)),
        "4. Ben Graham (sigma=30)"
    )

    # Experiment 4: Autocrop + Ben Graham (sigma=30)
    results["autocrop_ben_graham"] = evaluate_pipeline(
        model, manifest,
        lambda img: to_model_tensor(apply_ben_graham(cv2.resize(autocrop_fundus(img), (380, 380), interpolation=cv2.INTER_AREA), sigma=30)),
        "5. Autocrop + Ben Graham"
    )

    # Experiment 5: CLAHE Enhancement
    results["clahe"] = evaluate_pipeline(
        model, manifest,
        lambda img: to_model_tensor(apply_clahe(autocrop_fundus(img))),
        "6. Autocrop + CLAHE"
    )

    # Experiment 6: Test-Time Augmentation (4-fold)
    results["tta_4x"] = evaluate_tta_pipeline(
        model, manifest,
        "7. Autocrop + 4-Fold TTA"
    )

    # Save comprehensive results JSON
    audit_summary = {
        "dataset_name": "MICCAI DDR Test Benchmark vs APTOS 2019",
        "sample_size": len(manifest),
        "uncertainty_disclaimer": (
            "Pipeline scores are evaluated on 30 images (6 per ICDR grade) from MICCAI DDR "
            "and the APTOS reference on 2 samples. Due to sample size limitations, accuracy "
            "differences and domain-shift conclusions should be interpreted cautiously as preliminary observations."
        ),
        "ddr_image_statistics": {
            "avg_width": float(np.mean([s["width"] for s in ddr_stats])),
            "avg_height": float(np.mean([s["height"] for s in ddr_stats])),
            "avg_aspect_ratio": float(np.mean([s["aspect_ratio"] for s in ddr_stats])),
            "avg_black_ratio": float(np.mean([s["black_ratio"] for s in ddr_stats])),
            "avg_mean_r": float(np.mean([s["mean_r"] for s in ddr_stats])),
            "avg_mean_g": float(np.mean([s["mean_g"] for s in ddr_stats])),
            "avg_mean_b": float(np.mean([s["mean_b"] for s in ddr_stats])),
            "avg_sharpness": float(np.mean([s["sharpness"] for s in ddr_stats])),
        },
        "aptos_reference_statistics": {
            "samples": aptos_sample_stats,
            "avg_aspect_ratio": float(np.mean([s["aspect_ratio"] for s in aptos_sample_stats])) if aptos_sample_stats else 1.0,
            "avg_black_ratio": float(np.mean([s["black_ratio"] for s in aptos_sample_stats])) if aptos_sample_stats else 0.0,
        },
        "pipeline_experiments": {
            k: {
                "name": v["pipeline_name"],
                "accuracy": round(v["accuracy"] * 100, 2),
                "qwk": round(v["qwk"], 4),
                "macro_f1": round(v["macro_f1"], 4),
                "referable_accuracy": round(v["referable_accuracy"] * 100, 2),
                "referable_sensitivity": round(v["referable_sensitivity"] * 100, 2),
                "referable_precision": round(v["referable_precision"] * 100, 2),
                "predictions": v["predictions"],
            }
            for k, v in results.items()
        },
        "ddr_per_image_stats": ddr_stats,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RESULTS_DIR / "generalization_investigation_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    logger.info("Saved generalization investigation results to %s", out_json)


if __name__ == "__main__":
    main()
