"""Production WSGI entrypoint (for Waitress / Gunicorn)."""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.core.config import AppConfig
from src.app import create_app

config = AppConfig()
application = create_app(config)
app = application

