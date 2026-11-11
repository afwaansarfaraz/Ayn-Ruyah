"""Hospital screening analytics and clinical epidemiology endpoints."""

from flask import Blueprint, jsonify, current_app
from src.api.auth_middleware import require_tenant
from src.core.logging import logger

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/analytics", methods=["GET"])
@require_tenant
def get_analytics(tenant_id: str):
    """Calculates comprehensive DR screening performance metrics for the current hospital."""
    analytics_service = current_app.config["ANALYTICS_SERVICE"]
    try:
        data = analytics_service.get_hospital_analytics(tenant_id)
        return jsonify(data), 200
    except Exception as exc:
        logger.error("Error computing hospital analytics: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to calculate hospital screening analytics."}), 500

