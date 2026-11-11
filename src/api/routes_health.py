"""System health check and diagnostic status endpoints."""

from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)

@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Returns application runtime, model status, and capability info."""
    config = current_app.config["APP_CONFIG"]
    diag_service = current_app.config["DIAGNOSTIC_SERVICE"]
    model_loaded = diag_service.model is not None

    payload = {
        "status": "healthy",
        "model_loaded": model_loaded,
        "model": "EfficientNet-B4 (NoisyStudent)",
        "classes": config.num_classes,
        "device": str(config.device),
        "image_size": config.image_size,
        "gradcam": "Convolutional Head Activation Mapping with Retinal Masking",
        "preprocessing": "Ben Graham + ImageNet Normalization" if config.use_ben_graham else "ImageNet Standard",
        "trained_on": "APTOS 2019 Blindness Detection (5-Class)",
        "demo_mode": (not model_loaded) or config.allow_demo_mode or config.seed_demo_data,
    }
    return jsonify(payload), 200

