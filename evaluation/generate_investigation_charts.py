"""Generate high-resolution visual comparison charts for the Generalization Investigation Report."""

import json
import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
ARTIFACTS_DIR_ENV = os.environ.get("ARTIFACTS_DIR")
ARTIFACTS_DIR = Path(ARTIFACTS_DIR_ENV) if ARTIFACTS_DIR_ENV else None

def save_fig(filename: str):
    """Saves figure to primary RESULTS_DIR, and optionally to ARTIFACTS_DIR if configured and existing."""
    primary_path = RESULTS_DIR / filename
    plt.savefig(primary_path)
    if ARTIFACTS_DIR and ARTIFACTS_DIR.exists():
        plt.savefig(ARTIFACTS_DIR / filename)
    print(f"Saved: {primary_path}")

with open(RESULTS_DIR / "generalization_investigation_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Ground truth grades loaded dynamically from ddr_per_image_stats (aligned with prediction image order)
y_true = [item["grade"] for item in data["ddr_per_image_stats"]]
class_labels = ["G0 (None)", "G1 (Mild)", "G2 (Mod)", "G3 (Sev)", "G4 (PDR)"]

# -------------------------------------------------------------
# Chart 1: Pipeline Performance Comparison
# -------------------------------------------------------------
pipelines = [
    ("Direct Resize (Base)", data["pipeline_experiments"]["baseline_resize"]),
    ("Retinal Autocrop", data["pipeline_experiments"]["autocrop"]),
    ("Ben Graham (s=10)", data["pipeline_experiments"]["ben_graham_sigma10"]),
    ("Ben Graham (s=30)", data["pipeline_experiments"]["ben_graham_sigma30"]),
    ("Autocrop + Ben Graham", data["pipeline_experiments"]["autocrop_ben_graham"]),
    ("Autocrop + CLAHE", data["pipeline_experiments"]["clahe"]),
    ("Autocrop + 4x TTA", data["pipeline_experiments"]["tta_4x"]),
]

names = [p[0] for p in pipelines]
accs = [p[1]["accuracy"] for p in pipelines]
qwks = [p[1]["qwk"] * 100 for p in pipelines]
f1s = [p[1]["macro_f1"] * 100 for p in pipelines]
sens = [p[1]["referable_sensitivity"] for p in pipelines]

fig, ax = plt.subplots(figsize=(13, 6.5), dpi=200)
x = np.arange(len(names))
width = 0.20

rects1 = ax.bar(x - 1.5*width, accs, width, label="5-Class Accuracy (%)", color="#087E8B")
rects2 = ax.bar(x - 0.5*width, qwks, width, label="QWK (Kappa x100)", color="#16A779")
rects3 = ax.bar(x + 0.5*width, f1s, width, label="Macro F1-Score (%)", color="#F59E0B")
rects4 = ax.bar(x + 1.5*width, sens, width, label="Referable DR Sens (%)", color="#2563EB")

ax.set_ylabel("Score / Percentage (%)", fontsize=11, fontweight="bold", color="#142D4E")
ax.set_title("EfficientNet-B4 Out-of-Domain Generalization Across Preprocessing Strategies\n(MICCAI DDR Clinical Benchmark, N=30)", fontsize=13, fontweight="bold", color="#142D4E", pad=15)
ax.set_xticks(x)
ax.set_xticklabels(names, rotation=15, ha="right", fontsize=9.5, fontweight="600")
ax.legend(frameon=True, facecolor="#F5FAFF", edgecolor="#D0E3F3", fontsize=9.5)
ax.grid(axis="y", linestyle="--", alpha=0.3, color="#8395A7")
ax.set_ylim(0, 110)

# Annotate values on top of highest bars
for rects in [rects1, rects2, rects3, rects4]:
    for rect in rects:
        h = rect.get_height()
        if h > 15:
            ax.annotate(f"{h:.1f}",
                        xy=(rect.get_x() + rect.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7.5, color="#142D4E", fontweight="bold")

plt.tight_layout()
save_fig("generalization_experiment_comparison.png")
plt.close()

# -------------------------------------------------------------
# Chart 2: Side-by-Side Confusion Matrices (Baseline vs Ben Graham vs CLAHE)
# -------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(16, 5), dpi=200)

exp_base = data["pipeline_experiments"]["baseline_resize"]
exp_bg30 = data["pipeline_experiments"]["ben_graham_sigma30"]
exp_clahe = data["pipeline_experiments"]["clahe"]

to_compare = [
    (
        f"{exp_base['name']}\n(Acc: {exp_base['accuracy']:.1f}%, QWK: {exp_base['qwk']:.3f})",
        exp_base["predictions"],
        "Blues",
    ),
    (
        f"{exp_bg30['name']}\n(Acc: {exp_bg30['accuracy']:.1f}%, QWK: {exp_bg30['qwk']:.3f})",
        exp_bg30["predictions"],
        "Greens",
    ),
    (
        f"{exp_clahe['name']}\n(Acc: {exp_clahe['accuracy']:.1f}%, QWK: {exp_clahe['qwk']:.3f})",
        exp_clahe["predictions"],
        "YlGnBu",
    ),
]

for idx, (title, preds, cmap) in enumerate(to_compare):
    cm = confusion_matrix(y_true, preds, labels=[0, 1, 2, 3, 4])
    ax = axes[idx]
    im = ax.imshow(cm, interpolation="nearest", cmap=cmap)
    ax.set_title(title, fontsize=11, fontweight="bold", color="#142D4E", pad=10)
    tick_marks = np.arange(5)
    ax.set_xticks(tick_marks)
    ax.set_yticks(tick_marks)
    ax.set_xticklabels(class_labels, rotation=40, ha="right", fontsize=8)
    ax.set_yticklabels(class_labels, fontsize=8)
    ax.set_xlabel("Predicted Grade", fontsize=9, fontweight="bold", color="#142D4E")
    if idx == 0:
        ax.set_ylabel("True Grade", fontsize=9, fontweight="bold", color="#142D4E")

    # Annotate numbers
    thresh = cm.max() / 2.0
    for i in range(5):
        for j in range(5):
            val = cm[i, j]
            ax.text(j, i, format(val, "d"),
                    ha="center", va="center",
                    color="white" if val > thresh else "#142D4E",
                    fontweight="bold", fontsize=10)

plt.tight_layout()
save_fig("generalization_confusion_matrices.png")
plt.close()

# -------------------------------------------------------------
# Chart 3: Domain Shift Diagnostics (Aspect Ratio & Color Distribution)
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=200)

# 3A: Geometry & Margins
stats = data["ddr_image_statistics"]
ref = data["aptos_reference_statistics"]

metrics = ["Aspect Ratio (W/H)", "Black Border Margin (%)"]
ddr_vals = [stats["avg_aspect_ratio"], stats["avg_black_ratio"] * 100]
aptos_vals = [ref["avg_aspect_ratio"], ref["avg_black_ratio"] * 100]

x = np.arange(len(metrics))
width = 0.3
ax1.bar(x - width/2, aptos_vals, width, label="APTOS 2019 (Training Domain)", color="#087E8B")
ax1.bar(x + width/2, ddr_vals, width, label="MICCAI DDR (External Domain)", color="#EA580C")
ax1.set_title("Image Geometry & Black Margin Domain Shift", fontsize=11, fontweight="bold", color="#142D4E")
ax1.set_xticks(x)
ax1.set_xticklabels(metrics, fontsize=9.5, fontweight="600")
ax1.set_ylabel("Metric Value / Percentage (%)", fontsize=9.5, fontweight="bold")
ax1.legend(frameon=True, facecolor="#F5FAFF")
ax1.grid(axis="y", linestyle="--", alpha=0.3)

for rect in ax1.patches:
    h = rect.get_height()
    ax1.annotate(f"{h:.1f}",
                 xy=(rect.get_x() + rect.get_width() / 2, h),
                 xytext=(0, 3), textcoords="offset points",
                 ha="center", va="bottom", fontsize=9, color="#142D4E", fontweight="bold")

# 3B: Color Channel Mean Distribution
channels = ["Red Channel (Mean)", "Green Channel (Mean)", "Blue Channel (Mean)", "Laplacian Sharpness"]
ddr_c = [stats["avg_mean_r"], stats["avg_mean_g"], stats["avg_mean_b"], stats["avg_sharpness"]]
aptos_samples = ref["samples"]
aptos_c = [
    np.mean([s["mean_r"] for s in aptos_samples]),
    np.mean([s["mean_g"] for s in aptos_samples]),
    np.mean([s["mean_b"] for s in aptos_samples]),
    np.mean([s["sharpness"] for s in aptos_samples]),
]

x2 = np.arange(len(channels))
ax2.bar(x2 - width/2, aptos_c, width, label="APTOS 2019 Samples", color="#087E8B")
ax2.bar(x2 + width/2, ddr_c, width, label="MICCAI DDR Dataset", color="#EA580C")
ax2.set_title("Color Channel Means & High-Frequency Sharpness", fontsize=11, fontweight="bold", color="#142D4E")
ax2.set_xticks(x2)
ax2.set_xticklabels(channels, rotation=15, ha="right", fontsize=9, fontweight="600")
ax2.set_ylabel("Pixel Intensity / Variance", fontsize=9.5, fontweight="bold")
ax2.legend(frameon=True, facecolor="#F5FAFF")
ax2.grid(axis="y", linestyle="--", alpha=0.3)

for rect in ax2.patches:
    h = rect.get_height()
    ax2.annotate(f"{h:.1f}",
                 xy=(rect.get_x() + rect.get_width() / 2, h),
                 xytext=(0, 3), textcoords="offset points",
                 ha="center", va="bottom", fontsize=8.5, color="#142D4E", fontweight="bold")

plt.tight_layout()
save_fig("domain_shift_distributions.png")
plt.close()

