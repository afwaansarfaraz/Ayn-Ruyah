"""Model checkpoint loading and factory routines."""

import os
from pathlib import Path
from typing import Optional
import torch

from src.models.base import BaseDRModel
from src.models.efficientnet_b4 import EfficientNetB4DRModel
from src.core.config import AppConfig
from src.core.logging import logger


def load_model(config: AppConfig) -> Optional[BaseDRModel]:
    """Loads and initializes the Diabetic Retinopathy model from configured weights.

    Args:
        config: Application configuration instance.

    Returns:
        Loaded model in eval mode on target device, or None if weights not found.
    """
    weights_path = config.weights_path
    device = config.device

    if not weights_path or not os.path.exists(weights_path):
        if not config.allow_demo_mode:
            raise FileNotFoundError(
                f"Model checkpoint not found at: '{weights_path}'. "
                "The trained model weights must be placed at 'weights/best.pt'. "
                "To explicitly permit unweighted demo fallback, set ALLOW_DEMO_MODE=True."
            )
        logger.warning(
            "Model checkpoint not found at: %s. Application will run in DEMO MODE.",
            weights_path,
        )
        return None

    try:
        logger.info("[1/3] Instantiating EfficientNet-B4 architecture...")
        model = EfficientNetB4DRModel(
            num_classes=config.num_classes,
            hidden_dim=config.hidden_dim,
            dropout_pool=config.dropout_pool,
            dropout_hidden=config.dropout_hidden,
            stochastic_depth_rate=config.stochastic_depth_rate,
        )

        logger.info("[2/3] Loading weights from %s...", weights_path)
        if hasattr(torch.serialization, "add_safe_globals"):
            try:
                torch.serialization.add_safe_globals([torch.torch_version.TorchVersion])
            except Exception:
                pass

        checkpoint = torch.load(weights_path, map_location=device, weights_only=True)

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
            epoch = checkpoint.get("epoch", "N/A")
            metric = checkpoint.get("best_metric", "N/A")
            logger.info("Loaded checkpoint metadata: Epoch=%s, Val Metric=%s", epoch, metric)
        elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        else:
            state_dict = checkpoint

        model.load_state_dict(state_dict, strict=True)

        logger.info("[3/3] Moving model to %s and preparing eval mode...", device)
        model = model.to(device)
        model.eval()

        logger.info(
            "SUCCESS: EfficientNet-B4 loaded successfully on %s (Input: %dpx, Classes: %d)",
            device, config.image_size, config.num_classes,
        )
        return model

    except Exception as exc:
        logger.error("Failed to load model from %s: %s", weights_path, exc, exc_info=True)
        if not config.allow_demo_mode:
            raise RuntimeError(
                f"Failed to load checkpoint from {weights_path}: {exc}. "
                "Set ALLOW_DEMO_MODE=True if demo fallback is explicitly intended."
            ) from exc
        return None

