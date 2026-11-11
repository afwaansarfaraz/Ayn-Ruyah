# Legacy / Training Pipeline

This directory contains experimental and training scripts isolated from the production inference pipeline.

## Files
- `dr.py`: Early exploratory training script written by the original author.
  - **Architecture:** EfficientNet-B0 (via `timm`)
  - **Task:** Binary classification (Grade 0 vs. Grades 1–4 binarized to `1`)
  - **Resolution:** 224 × 224 pixels
  - **Dataset:** Local APTOS 2019 Blindness Detection dataset

## Why this is isolated from production
1. **Incompatible Class Head:** Production requires 5-class severity grading (Grade 0 to Grade 4). `dr.py` modifies the classifier head to 2 output classes (`nn.Linear(..., 2)`).
2. **Incompatible Backbone:** Production uses `tf_efficientnet_b4_ns` ($1792$ latent features at $380 \times 380$ input), whereas `dr.py` uses `efficientnet_b0` ($1280$ latent features at $224 \times 224$ input).
3. **Decoupling Production & Training:** Production runtime never depends on raw training loaders, `torch.optim`, or ad-hoc training loops.

