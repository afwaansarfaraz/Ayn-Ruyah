"""Unit tests for the OpenCV heuristic retinal image validator."""

import pytest
from PIL import Image
import io

from src.services.image_validator import RetinalImageValidator
from src.core.exceptions import InvalidRetinalImageError


def test_validator_passes_sample_grade0(sample_grade0_bytes):
    validator = RetinalImageValidator()
    img = Image.open(io.BytesIO(sample_grade0_bytes))
    is_valid, reason = validator.validate(img)
    assert is_valid is True
    assert reason == "OK"


def test_validator_passes_sample_grade3(sample_grade3_bytes):
    validator = RetinalImageValidator()
    img = Image.open(io.BytesIO(sample_grade3_bytes))
    is_valid, reason = validator.validate(img)
    assert is_valid is True
    assert reason == "OK"


def test_validator_rejects_white_image(non_retinal_image_bytes):
    validator = RetinalImageValidator()
    img = Image.open(io.BytesIO(non_retinal_image_bytes))
    is_valid, reason = validator.validate(img)
    assert is_valid is False
    assert "retinal fundus scan" in reason


def test_validator_raises_exception_on_invalid_image(non_retinal_image_bytes):
    validator = RetinalImageValidator()
    img = Image.open(io.BytesIO(non_retinal_image_bytes))
    with pytest.raises(InvalidRetinalImageError) as exc_info:
        validator.verify_or_raise(img)
    assert "fundus photograph" in str(exc_info.value)

