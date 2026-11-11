"""Pytest fixtures and test environment configuration."""

import os
import sys
from pathlib import Path
import pytest
from PIL import Image
import io

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long-for-testing")
os.environ.setdefault("ALLOW_DEMO_MODE", "True")

from src.core.config import AppConfig
from src.app import create_app


@pytest.fixture(scope="session")
def app_config(tmp_path_factory):
    """Provides application configuration targeting an isolated temporary test database."""
    test_data_dir = tmp_path_factory.mktemp("retinalens_test_data")
    test_db = test_data_dir / "test_retinalens.db"
    test_uploads = test_data_dir / "test_uploads"
    test_uploads.mkdir(parents=True, exist_ok=True)
    return AppConfig(
        debug=False,
        seed_demo_data=True,
        secret_key="test-secret-key-32-chars-long-for-testing",
        data_dir=test_data_dir,
        db_path=test_db,
        uploads_dir=test_uploads,
    )


@pytest.fixture(scope="session")
def app(app_config):
    """Provides initialized Flask application for testing."""
    application = create_app(app_config)
    application.config["TESTING"] = True
    return application


@pytest.fixture(scope="session")
def client(app):
    """Provides Flask test client."""
    return app.test_client()


@pytest.fixture(scope="session")
def sample_grade0_bytes():
    """Returns raw bytes of sample grade 0 retinal fundus image."""
    img_path = PROJECT_ROOT / "sample_images" / "grade0_14197_left-600.jpg"
    with open(img_path, "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def sample_grade3_bytes():
    """Returns raw bytes of sample grade 3 retinal fundus image."""
    img_path = PROJECT_ROOT / "sample_images" / "grade3_6b128e648646-600-FS.jpg"
    with open(img_path, "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def non_retinal_image_bytes():
    """Returns raw bytes of an artificial non-retinal image (white canvas)."""
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

