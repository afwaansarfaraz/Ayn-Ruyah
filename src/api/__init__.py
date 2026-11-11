"""API blueprint package exports."""

from src.api.routes_health import health_bp
from src.api.routes_diagnostics import diagnostics_bp
from src.api.routes_web import web_bp
from src.api.routes_auth import auth_bp
from src.api.routes_tenants import tenants_bp
from src.api.routes_patients import patients_bp
from src.api.routes_screenings import screenings_bp
from src.api.routes_analytics import analytics_bp

__all__ = [
    "health_bp",
    "diagnostics_bp",
    "web_bp",
    "auth_bp",
    "tenants_bp",
    "patients_bp",
    "screenings_bp",
    "analytics_bp",
]
