"""Abstract base class interface for Diabetic Retinopathy models."""

import abc
import torch
import torch.nn as nn

class BaseDRModel(abc.ABC, nn.Module):
    """Abstract base class for Diabetic Retinopathy classification models."""

    @abc.abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass taking (B, 3, H, W) images and returning (B, num_classes) logits."""
        pass

    @abc.abstractmethod
    def get_target_layer_for_gradcam(self) -> nn.Module:
        """Returns the convolutional layer module targeted by Grad-CAM explainability."""
        pass

