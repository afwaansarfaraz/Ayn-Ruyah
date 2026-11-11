"""Centralized application configuration with environment variable support."""

import os
import secrets
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
import torch

@dataclass
class AppConfig:
    """Application and Model Configuration settings."""
    # Base paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    frontend_dir: Path = Path(__file__).resolve().parent.parent.parent / "frontend"
    weights_dir: Path = Path(__file__).resolve().parent.parent.parent / "weights"
    data_dir: Path = Path(__file__).resolve().parent.parent.parent / "data"
    db_path: Path = Path(__file__).resolve().parent.parent.parent / "data" / "retinalens.db"
    uploads_dir: Path = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"
    secret_key: str = os.getenv("SECRET_KEY", "")

    # Server settings
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "5000"))
    debug: bool = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    # Operational settings
    seed_demo_data: bool = os.getenv("SEED_DEMO_DATA", "False").lower() in ("true", "1", "yes")
    allow_demo_mode: bool = os.getenv("ALLOW_DEMO_MODE", "False").lower() in ("true", "1", "yes")
    cors_allowed_origins: List[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://127.0.0.1:5000,http://localhost:5000",
            ).split(",")
            if o.strip()
        ]
    )

    # Deep Learning Settings (Exact match for anishanish383/dr-detection-efficientnet-b4)
    model_name: str = "tf_efficientnet_b4_ns"
    image_size: int = int(os.getenv("IMAGE_SIZE", "380"))
    num_classes: int = 5
    stochastic_depth_rate: float = 0.2
    hidden_dim: int = 256
    dropout_pool: float = 0.4
    dropout_hidden: float = 0.3
    use_ben_graham: bool = os.getenv("USE_BEN_GRAHAM", "False").lower() in ("true", "1", "yes")

    # Weights resolution: Priority order:
    # 1. MODEL_PATH env variable
    # 2. weights/best.pt (recommended primary model)
    # 3. best.pt in root
    # 4. best_model.pth in root
    weights_path: str = ""

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        # Validate secret key
        if not self.secret_key:
            if not self.debug:
                raise ValueError("SECRET_KEY environment variable is required when debug is disabled.")
            self.secret_key = secrets.token_hex(32)

        env_path = os.getenv("MODEL_PATH")
        if env_path and os.path.exists(env_path):
            self.weights_path = os.path.abspath(env_path)
            return

        candidates = [
            self.weights_dir / "best.pt",
            self.base_dir / "best.pt",
            self.weights_dir / "best_model.pth",
            self.base_dir / "best_model.pth",
        ]
        for c in candidates:
            if c.exists():
                self.weights_path = str(c.resolve())
                return

        # Default fallback target if none exists yet
        self.weights_path = str((self.weights_dir / "best.pt").resolve())

    @property
    def device(self) -> torch.device:
        device_str = os.getenv("DEVICE")
        if device_str:
            return torch.device(device_str)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

