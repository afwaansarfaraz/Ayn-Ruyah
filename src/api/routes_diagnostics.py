"""Diabetic Retinopathy image analysis endpoints."""

from flask import Blueprint, request, jsonify, current_app

from src.api.auth_middleware import require_tenant
from src.core.exceptions import InvalidRetinalImageError
from src.core.logging import logger

diagnostics_bp = Blueprint("diagnostics", __name__)

@diagnostics_bp.route("/api/analyze", methods=["POST"])
@require_tenant
def analyze_scan():
    """Analyzes an uploaded retinal fundus scan and returns severity grading + Grad-CAM heatmap."""
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image provided"}), 400

        image_file = request.files["image"]
        image_bytes = image_file.read()

        if not image_bytes:
            return jsonify({"error": "Empty image payload provided"}), 400

        diagnostic_service = current_app.config["DIAGNOSTIC_SERVICE"]
        result = diagnostic_service.analyze_image_bytes(image_bytes)

        return jsonify(result.to_dict()), 200

    except InvalidRetinalImageError as val_err:
        logger.warning("Retinal validation rejected image: %s", val_err.message)
        return jsonify({"error": val_err.message}), 400

    except Exception as exc:
        logger.error("Analysis route error: %s", exc, exc_info=True)
        return jsonify({"error": "Internal diagnostic analysis error."}), 500

