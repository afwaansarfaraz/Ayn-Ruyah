"""Unit tests for the reconstructed EfficientNet-B4 architecture and head."""

import torch
from src.models.efficientnet_b4 import ClassificationHead, EfficientNetB4DRModel


def test_classification_head_shape():
    head = ClassificationHead(in_features=1792, num_classes=5, hidden_dim=256)
    dummy_features = torch.randn(2, 1792)

    logits = head(dummy_features)

    assert logits.shape == (2, 5)


def test_efficientnet_b4_forward_pass():
    model = EfficientNetB4DRModel(num_classes=5, hidden_dim=256)
    model.eval()

    dummy_image = torch.randn(1, 3, 380, 380)
    with torch.no_grad():
        output = model(dummy_image)

    assert output.shape == (1, 5)
    assert model.get_target_layer_for_gradcam() is not None

