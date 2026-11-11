"""Image preprocessing service supporting standard ImageNet and Ben Graham pipelines."""

from typing import Tuple
import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image

from src.core.constants import IMAGENET_MEAN, IMAGENET_STD
from src.core.config import AppConfig


class RetinalPreprocessor:
    """Prepares raw retinal images for model inference."""

    def __init__(self, config: AppConfig):
        self.image_size = config.image_size
        self.device = config.device
        self.use_ben_graham = config.use_ben_graham

        self.standard_transform = transforms.Compose([
            transforms.Resize((self.image_size, self.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

    def preprocess(self, image: Image.Image) -> torch.Tensor:
        """Transforms input PIL image into model-ready tensor (1, 3, H, W).

        Args:
            image: Input PIL Image.

        Returns:
            Preprocessed torch.Tensor ready for model forward pass.
        """
        if self.use_ben_graham:
            return self._ben_graham_preprocess(image)
        return self._standard_preprocess(image)

    def _standard_preprocess(self, image: Image.Image) -> torch.Tensor:
        rgb_image = image.convert("RGB")
        tensor = self.standard_transform(rgb_image)
        return tensor.unsqueeze(0).to(self.device)

    def _ben_graham_preprocess(
        self, image: Image.Image, sigma_ratio: float = 0.1, add_back: int = 128
    ) -> torch.Tensor:
        # Convert PIL to BGR array for OpenCV operations
        rgb_arr = np.array(image.convert("RGB"))
        bgr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

        # 1. Resize
        img = cv2.resize(bgr, (self.image_size, self.image_size))

        # 2. Circular mask
        mask = np.zeros((self.image_size, self.image_size), dtype=np.uint8)
        center = self.image_size // 2
        radius = int(self.image_size * 0.45)
        cv2.circle(mask, (center, center), radius, 255, -1)

        # 3. Local average subtraction
        sigma = int(self.image_size * sigma_ratio)
        if sigma % 2 == 0:
            sigma += 1
        blur = cv2.GaussianBlur(img, (0, 0), sigma)
        img = cv2.addWeighted(img, 4, blur, -4, add_back)
        img = cv2.bitwise_and(img, img, mask=mask)

        # 4. Normalize to [0, 1] RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # 5. ImageNet standard normalization
        mean = np.array(IMAGENET_MEAN, dtype=np.float32)
        std = np.array(IMAGENET_STD, dtype=np.float32)
        img_norm = (img_rgb - mean) / std

        # Transpose HWC -> CHW
        tensor = torch.from_numpy(img_norm.transpose(2, 0, 1))
        return tensor.unsqueeze(0).to(self.device)

