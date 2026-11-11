"""Pytest test suite validating model evaluation outputs, metrics, and manifest."""

import json
from pathlib import Path
import pytest

@pytest.fixture
def eval_dir():
    return Path(__file__).resolve().parent.parent / "data" / "evaluation_dataset"

@pytest.fixture
def results_dir():
    return Path(__file__).resolve().parent.parent / "evaluation" / "results"

def test_evaluation_manifest_integrity(eval_dir):
    manifest_path = eval_dir / "ground_truth_manifest.json"
    assert manifest_path.exists(), "Evaluation manifest must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert len(manifest) == 30, "Benchmark must contain exactly 30 images"
    
    grade_counts = {}
    for entry in manifest:
        grade = entry["ground_truth_grade"]
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        img_path = eval_dir / "images" / entry["filename"]
        assert img_path.exists(), f"Image {entry['filename']} must exist on disk"
        assert img_path.stat().st_size > 50_000, f"Image {entry['filename']} must be a valid fundus file"

    for g in range(5):
        assert grade_counts[g] == 6, f"Grade {g} must have exactly 6 images (balanced)"

def test_evaluation_metrics_validity(results_dir):
    pointer_path = results_dir / "active_version.json"
    if pointer_path.exists():
        with open(pointer_path, "r", encoding="utf-8") as f:
            pointer = json.load(f)
        v_path = Path(pointer["version_path"])
        version_dir = v_path if v_path.is_absolute() else (results_dir / v_path)
    else:
        version_dir = results_dir

    metrics_path = version_dir / "evaluation_metrics.json"
    preds_path = version_dir / "predictions_table.json"
    assert metrics_path.exists(), "Evaluation metrics JSON must exist"
    assert preds_path.exists(), "Predictions table JSON must exist"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    with open(preds_path, "r", encoding="utf-8") as f:
        preds = json.load(f)

    # Recompute accuracy independently from individual predictions
    y_true = [p["ground_truth_grade"] for p in preds]
    y_pred = [p["predicted_grade"] for p in preds]
    recomputed_accuracy = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp) / len(y_true)

    assert abs(metrics["overall_accuracy"] - recomputed_accuracy) < 1e-5
    assert -1.0 <= metrics["quadratic_weighted_kappa"] <= 1.0
    assert 0.0 <= metrics["overall_accuracy"] <= 1.0
    assert 0.0 <= metrics["macro_f1"] <= 1.0

    assert len(metrics["per_class_metrics"]) == 5
    for g in range(5):
        grade_key = f"grade_{g}"
        assert grade_key in metrics["per_class_metrics"]
        cm = metrics["per_class_metrics"][grade_key]
        assert "precision" in cm
        assert "recall" in cm
        assert "f1_score" in cm
        assert cm["support"] == 6

def test_evaluation_generated_visualizations(results_dir):
    raw_cm = results_dir / "confusion_matrix_raw.png"
    norm_cm = results_dir / "confusion_matrix_normalized.png"
    bar_chart = results_dir / "per_class_metrics_bar.png"
    gradcam_gallery = results_dir / "gradcam_gallery.png"

    assert raw_cm.exists() and raw_cm.stat().st_size > 10_000
    assert norm_cm.exists() and norm_cm.stat().st_size > 10_000
    assert bar_chart.exists() and bar_chart.stat().st_size > 10_000
    assert gradcam_gallery.exists() and gradcam_gallery.stat().st_size > 50_000

def test_predictions_table_structure(results_dir):
    pointer_path = results_dir / "active_version.json"
    if pointer_path.exists():
        with open(pointer_path, "r", encoding="utf-8") as f:
            pointer = json.load(f)
        v_path = Path(pointer["version_path"])
        version_dir = v_path if v_path.is_absolute() else (results_dir / v_path)
    else:
        version_dir = results_dir

    preds_path = version_dir / "predictions_table.json"
    assert preds_path.exists(), f"Active predictions table JSON must exist at {preds_path}"

    with open(preds_path, "r", encoding="utf-8") as f:
        preds = json.load(f)

    assert len(preds) == 30
    for p in preds:
        assert "image_id" in p
        assert "ground_truth_grade" in p
        assert "predicted_grade" in p
        assert "confidence_percent" in p
        assert "correct" in p
        assert "prob_grade0" in p
        assert "prob_grade4" in p
        assert 0 <= p["predicted_grade"] <= 4
        assert 0.0 < p["confidence_percent"] <= 100.0


def test_evaluation_versioning_and_active_pointer(results_dir):
    pointer_path = results_dir / "active_version.json"
    assert pointer_path.exists(), "active_version.json pointer must exist"

    with open(pointer_path, "r", encoding="utf-8") as f:
        pointer = json.load(f)

    assert "active_version" in pointer
    assert "version_path" in pointer
    v_path = Path(pointer["version_path"])
    version_dir = v_path if v_path.is_absolute() else (results_dir / v_path)
    assert version_dir.exists(), f"Active version directory {version_dir} must exist"
    assert (version_dir / "evaluation_metrics.json").exists()
    assert (version_dir / "predictions_table.json").exists()
    assert (version_dir / "gradcam").is_dir()

