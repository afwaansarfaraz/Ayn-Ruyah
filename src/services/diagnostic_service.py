"""Diagnostic orchestration service coordinating validation, preprocessing, inference, and explainability."""

import io
import random
import threading
from typing import Optional, Dict
import cv2
import numpy as np
from PIL import Image
import torch

from src.models.base import BaseDRModel
from src.services.image_validator import RetinalImageValidator
from src.services.preprocessing import RetinalPreprocessor
from src.services.gradcam import GradCAMService
from src.schemas.responses import DiagnosticResult
from src.core.constants import (
    NUM_CLASSES,
    GRADE_LABELS,
    GRADE_SEVERITY,
    GRADE_COLORS,
    GRADE_RECOMMENDATIONS,
)
from src.core.exceptions import InvalidRetinalImageError
from src.core.logging import logger


class DiagnosticService:
    """Orchestrates end-to-end retinal image diagnostic workflow."""

    def __init__(
        self,
        model: Optional[BaseDRModel],
        validator: RetinalImageValidator,
        preprocessor: RetinalPreprocessor,
        gradcam: GradCAMService,
    ):
        self.model = model
        self.validator = validator
        self.preprocessor = preprocessor
        self.gradcam = gradcam
        self._inference_lock = threading.Lock()

    def analyze_image_bytes(self, image_bytes: bytes) -> DiagnosticResult:
        """Executes full diagnostic pipeline on uploaded image bytes."""
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            raise InvalidRetinalImageError(f"Invalid image format: {str(exc)}") from exc

        # 1. Retinal Image Verification
        self.validator.verify_or_raise(image)

        original_arr = np.array(image)
        original_bgr = cv2.cvtColor(original_arr, cv2.COLOR_RGB2BGR)

        # 2. Fallback if model weights are absent
        if self.model is None:
            logger.warning("Executing in DEMO MODE (model weights not loaded).")
            return self._generate_demo_result(original_bgr)

        # 3. Real Deep Learning Inference (serialized across threads)
        image_tensor = self.preprocessor.preprocess(image)

        with self._inference_lock:
            # Forward pass with gradient tracking for Grad-CAM
            self.model.zero_grad()
            outputs = self.model(image_tensor)

            probabilities = torch.softmax(outputs, dim=1)[0].detach()
            predicted = int(torch.argmax(probabilities).item())
            confidence = float(probabilities[predicted].item() * 100.0)

            # Backward pass for Grad-CAM on predicted class
            one_hot = torch.zeros_like(outputs)
            one_hot[0, predicted] = 1.0
            outputs.backward(gradient=one_hot)

            # Generate explainability heatmap
            heatmap_b64 = self.gradcam.generate(image_tensor, predicted, original_bgr)

        # Build probabilities dictionary
        prob_dict: Dict[str, float] = {
            GRADE_LABELS[i]: round(float(probabilities[i].item() * 100.0), 2)
            for i in range(NUM_CLASSES)
        }

        return DiagnosticResult(
            grade=predicted,
            result=GRADE_LABELS[predicted],
            severity=GRADE_SEVERITY[predicted],
            confidence=confidence,
            color=GRADE_COLORS[predicted],
            recommendation=GRADE_RECOMMENDATIONS[predicted],
            probabilities=prob_dict,
            heatmap=heatmap_b64,
            demo_mode=False,
        )

    def _generate_demo_result(self, original_bgr: np.ndarray) -> DiagnosticResult:
        demo_grade = random.randint(0, 4)
        prob_dict = {GRADE_LABELS[i]: round(100.0 / NUM_CLASSES, 2) for i in range(NUM_CLASSES)}
        heatmap_b64 = self.gradcam.generate_demo_heatmap(original_bgr)

        return DiagnosticResult(
            grade=demo_grade,
            result=GRADE_LABELS[demo_grade],
            severity=GRADE_SEVERITY[demo_grade],
            confidence=round(random.uniform(70.0, 95.0), 2),
            color=GRADE_COLORS[demo_grade],
            recommendation=GRADE_RECOMMENDATIONS[demo_grade],
            probabilities=prob_dict,
            heatmap=heatmap_b64,
            demo_mode=True,
        )

