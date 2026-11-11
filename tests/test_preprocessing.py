"""Unit tests for standard and Ben Graham retinal image preprocessing."""

import io
import torch
from PIL import Image

from src.core.config import AppConfig
from src.services.preprocessing import RetinalPreprocessor


def test_standard_preprocessing(sample_grade0_bytes):
    config = AppConfig(image_size=380, use_ben_graham=False)
    preprocessor = RetinalPreprocessor(config)
    img = Image.open(io.BytesIO(sample_grade0_bytes))

    tensor = preprocessor.preprocess(img)

    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (1, 3, 380, 380)
    assert tensor.dtype == torch.float32


def test_ben_graham_preprocessing(sample_grade3_bytes):
    config = AppConfig(image_size=380, use_ben_graham=True)
    preprocessor = RetinalPreprocessor(config)
    img = Image.open(io.BytesIO(sample_grade3_bytes))

    tensor = preprocessor.preprocess(img)

    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (1, 3, 380, 380)
    assert tensor.dtype == torch.float32

