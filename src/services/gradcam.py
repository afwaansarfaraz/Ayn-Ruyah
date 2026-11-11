"""Grad-CAM explainability service with clinical eye-masking."""

import base64
from typing import Optional
import cv2
import numpy as np
import torch
import torch.nn as nn

from src.models.base import BaseDRModel
from src.core.logging import logger


class GradCAMService:
    """Computes Gradient-weighted Class Activation Mapping with fundus eye-masking."""

    def __init__(self, model: Optional[BaseDRModel]):
        self.model = model
        self.activations: Optional[torch.Tensor] = None
        self.gradients: Optional[torch.Tensor] = None
        self.forward_hook = None
        self.backward_hook = None

        if self.model is not None:
            self._register_hooks()

    def _register_hooks(self) -> None:
        """Hooks into the model's last convolutional layer."""
        try:
            target_layer = self.model.get_target_layer_for_gradcam()
            self.forward_hook = target_layer.register_forward_hook(self._save_activations)
            self.backward_hook = target_layer.register_full_backward_hook(self._save_gradients)
            logger.info("Grad-CAM hooks successfully registered on target layer: %s", target_layer)
        except Exception as exc:
            logger.error("Failed to register Grad-CAM hooks: %s", exc)

    def _save_activations(self, module, inp, output) -> None:
        self.activations = output.detach()

    def _save_gradients(self, module, grad_input, grad_output) -> None:
        self.gradients = grad_output[0].detach()

    def generate(
        self,
        image_tensor: torch.Tensor,
        target_class: int,
        original_bgr: np.ndarray,
    ) -> str:
        """Generates Grad-CAM overlay heatmap encoded as base64 PNG string."""
        if self.model is None:
            return self.generate_demo_heatmap(original_bgr)

        if self.activations is None or self.gradients is None:
            raise RuntimeError("Grad-CAM generation failed: model activations or gradients were not captured.")

        h_orig, w_orig = original_bgr.shape[:2]

        # Weights: Global average pooling over spatial dimensions
        # self.gradients: [B, C, H, W] -> mean(dim=(2, 3))
        if len(self.gradients.shape) == 4:
            weights = self.gradients[0].mean(dim=(1, 2))  # [C]
            activations = self.activations[0]             # [C, H, W]
        else:
            weights = self.gradients.mean(dim=(2, 3))[0]
            activations = self.activations[0]

        cam = torch.zeros(activations.shape[1:], dtype=torch.float32, device=activations.device)
        for i, w in enumerate(weights):
            cam += w * activations[i]

        cam = torch.clamp(cam, min=0)
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)
        cam_np = cam.cpu().numpy()

        # Resize CAM to match original image dimensions
        cam_np = cv2.resize(cam_np, (w_orig, h_orig))

        # Build eye mask to prevent hotspots leaking into the dark background
        gray = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        _, eye_mask = cv2.threshold(blurred, 15, 255, cv2.THRESH_BINARY)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        eye_mask = cv2.morphologyEx(eye_mask, cv2.MORPH_CLOSE, k)
        eye_mask = cv2.morphologyEx(eye_mask, cv2.MORPH_OPEN, k)

        # Zero out values outside the retinal disc
        cam_np[eye_mask == 0] = 0
        heatmap = cv2.applyColorMap(np.uint8(255 * cam_np), cv2.COLORMAP_JET)
        heatmap[eye_mask == 0] = [0, 0, 0]

        # Blend original fundus photograph with Grad-CAM heatmap (60% image, 40% heatmap)
        overlay = cv2.addWeighted(original_bgr, 0.6, heatmap, 0.4, 0)

        # Encode to Base64 PNG
        _, buf = cv2.imencode(".png", overlay)
        return f"data:image/png;base64,{base64.b64encode(buf).decode()}"

    @staticmethod
    def generate_demo_heatmap(original_bgr: np.ndarray) -> str:
        """Generates synthetic radial distance heatmap for fallback/demo mode."""
        h, w = original_bgr.shape[:2]
        cx, cy = w // 2, h // 2
        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        dummy = np.uint8(255 * (1 - dist / dist.max()))
        heatmap = cv2.applyColorMap(dummy, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(original_bgr, 0.6, heatmap, 0.4, 0)
        _, buf = cv2.imencode(".png", overlay)
        return f"data:image/png;base64,{base64.b64encode(buf).decode()}"

    def cleanup(self) -> None:
        """Removes registered PyTorch hooks."""
        if self.forward_hook is not None:
            self.forward_hook.remove()
        if self.backward_hook is not None:
            self.backward_hook.remove()

