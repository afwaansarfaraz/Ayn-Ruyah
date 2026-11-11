"""Application entry point for running RetinaLens AI."""

import os
import sys

# Ensure project root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.core.config import AppConfig
from src.app import create_app

config = AppConfig()
app = create_app(config)


def main():
    """Runs the RetinaLens AI Flask application server."""
    print("=" * 70)
    print("RetinaLens AI — EfficientNet-B4 | 5-Class DR Detection")
    print(f"Server URL: http://{config.host}:{config.port}")
    print(f"Device    : {config.device}")
    print(f"Weights   : {config.weights_path}")
    print("=" * 70)
    app.run(host=config.host, port=config.port, debug=config.debug)


if __name__ == "__main__":
    main()

