"""EfficientNet-B4 model with custom classification head for 5-class DR grading.

Architecture specification (matching anishanish383/dr-detection-efficientnet-b4):
- Backbone: tf_efficientnet_b4_ns (NoisyStudent pretrained weights via timm)
- Head: GAP -> BatchNorm1d(1792) -> Dropout(0.4) -> Linear(1792, 256) -> ReLU -> Dropout(0.3) -> Linear(256, 5)
- Input: 380x380x3 RGB
"""

from typing import Optional
import torch
import torch.nn as nn
import timm

from src.models.base import BaseDRModel
from src.core.logging import logger


class ClassificationHead(nn.Module):
    """Two-stage regularized classification head."""

    def __init__(
        self,
        in_features: int = 1792,
        num_classes: int = 5,
        hidden_dim: int = 256,
        dropout_pool: float = 0.4,
        dropout_hidden: float = 0.3,
        use_batchnorm: bool = True,
        activation: str = "relu",
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []

        if use_batchnorm:
            layers.append(nn.BatchNorm1d(in_features))

        layers.append(nn.Dropout(dropout_pool))
        layers.append(nn.Linear(in_features, hidden_dim))

        if activation == "relu":
            layers.append(nn.ReLU(inplace=True))
        elif activation == "gelu":
            layers.append(nn.GELU())

        layers.append(nn.Dropout(dropout_hidden))
        layers.append(nn.Linear(hidden_dim, num_classes))

        self.head = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(x)


class EfficientNetB4DRModel(BaseDRModel):
    """Production EfficientNet-B4 Diabetic Retinopathy Classifier."""

    def __init__(
        self,
        num_classes: int = 5,
        hidden_dim: int = 256,
        dropout_pool: float = 0.4,
        dropout_hidden: float = 0.3,
        stochastic_depth_rate: float = 0.2,
    ) -> None:
        super().__init__()

        # Backbone without default classifier
        self.backbone = timm.create_model(
            "tf_efficientnet_b4_ns",
            pretrained=False,
            num_classes=0,
            global_pool="avg",
            drop_path_rate=stochastic_depth_rate,
        )

        in_features = self.backbone.num_features  # 1792

        # Classification Head
        self.head = ClassificationHead(
            in_features=in_features,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            dropout_pool=dropout_pool,
            dropout_hidden=dropout_hidden,
            use_batchnorm=True,
            activation="relu",
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        return self.head(features)

    def get_target_layer_for_gradcam(self) -> nn.Module:
        """Returns the last convolutional layer module in the backbone."""
        return self.backbone.conv_head

