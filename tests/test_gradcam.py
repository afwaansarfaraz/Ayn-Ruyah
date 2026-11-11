"""Unit tests for Grad-CAM explainability generation."""

import numpy as np
import torch
from src.models.efficientnet_b4 import EfficientNetB4DRModel
from src.services.gradcam import GradCAMService


def test_gradcam_hook_and_generation():
    model = EfficientNetB4DRModel(num_classes=5)
    model.eval()

    gradcam = GradCAMService(model)
    dummy_input = torch.randn(1, 3, 380, 380, requires_grad=True)
    dummy_bgr = np.zeros((380, 380, 3), dtype=np.uint8)
    dummy_bgr[50:330, 50:330] = [30, 50, 180]  # Simulate bright disc region

    # Run forward pass and backward pass
    output = model(dummy_input)
    one_hot = torch.zeros_like(output)
    one_hot[0, 3] = 1.0
    output.backward(gradient=one_hot)

    heatmap_b64 = gradcam.generate(dummy_input, target_class=3, original_bgr=dummy_bgr)

    assert isinstance(heatmap_b64, str)
    assert heatmap_b64.startswith("data:image/png;base64,")

    gradcam.cleanup()


def test_gradcam_demo_fallback():
    dummy_bgr = np.zeros((200, 200, 3), dtype=np.uint8)
    demo_heatmap_b64 = GradCAMService.generate_demo_heatmap(dummy_bgr)

    assert isinstance(demo_heatmap_b64, str)
    assert demo_heatmap_b64.startswith("data:image/png;base64,")

