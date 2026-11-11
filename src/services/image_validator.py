"""OpenCV heuristic validation service for retinal fundus images."""

from typing import Tuple
import cv2
import numpy as np
from PIL import Image

from src.core.exceptions import InvalidRetinalImageError
from src.core.logging import logger


class RetinalImageValidator:
    """Validates whether an uploaded image matches retinal fundus photography characteristics."""

    @staticmethod
    def validate(image: Image.Image) -> Tuple[bool, str]:
        """Performs 3-tier validation checks.

        Args:
            image: PIL Image object.

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        try:
            arr = np.array(image.convert("RGB").resize((256, 256)))
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            h, w = gray.shape

            # 1. Dark Corners vs Bright Center Check
            corner_size = 30
            corners = [
                gray[:corner_size, :corner_size],
                gray[:corner_size, -corner_size:],
                gray[-corner_size:, :corner_size],
                gray[-corner_size:, -corner_size:],
            ]
            corner_mean = float(np.mean([c.mean() for c in corners]))
            cx, cy = w // 2, h // 2
            r = min(w, h) // 4
            centre_mean = float(gray[cy - r : cy + r, cx - r : cx + r].mean())

            if corner_mean > 60:
                return False, "Image does not appear to be a retinal fundus scan (corners not dark). Please upload a valid fundus photograph."
            if centre_mean < corner_mean + 10:
                return False, "Image does not appear to be a retinal fundus scan (insufficient central illumination). Please upload a valid fundus photograph."

            # 2. Circular Disc Geometry Check
            blurred = cv2.GaussianBlur(gray, (15, 15), 0)
            _, bw = cv2.threshold(blurred, 15, 255, cv2.THRESH_BINARY)
            cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                return False, "No retinal disc detected. Please upload a valid fundus photograph."

            largest = max(cnts, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            hull_area = cv2.contourArea(cv2.convexHull(largest))

            if hull_area > 0 and (area / hull_area) < 0.6:
                return False, "Contour morphology does not match a retinal disc. Please upload a valid fundus photograph."
            if area < (h * w * 0.20):
                return False, "Retinal disc region occupies less than 20% of image. Please upload a valid fundus photograph."

            # 3. Red / Orange Spectrum Check
            r_mean = float(arr[:, :, 0].mean())
            g_mean = float(arr[:, :, 1].mean())
            b_mean = float(arr[:, :, 2].mean())

            if not (r_mean > g_mean and r_mean > b_mean and r_mean > 30):
                return False, "Image colour profile does not match a retinal fundus scan. Please upload a valid fundus photograph."

            return True, "OK"

        except Exception as exc:
            logger.error("Validation error during image processing: %s", exc, exc_info=True)
            return False, "Unable to validate image. Please upload a valid retinal fundus scan."

    def verify_or_raise(self, image: Image.Image) -> None:
        """Validates image and raises InvalidRetinalImageError if invalid."""
        is_valid, reason = self.validate(image)
        if not is_valid:
            raise InvalidRetinalImageError(reason)

