"""RetinaLens AI Multi-Tenant Diabetic Retinopathy Platform Application Factory."""

from typing import Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from src.core.config import AppConfig
from src.core.exceptions import RetinaLensException
from src.core.logging import logger
from src.database.connection import Database
from src.database.seeds import seed_database
from src.models.loader import load_model
from src.services.image_validator import RetinalImageValidator
from src.services.preprocessing import RetinalPreprocessor
from src.services.gradcam import GradCAMService
from src.services.diagnostic_service import DiagnosticService
from src.services.tenant_service import TenantService
from src.services.user_service import UserService
from src.services.patient_service import PatientService
from src.services.screening_service import ScreeningService
from src.services.analytics_service import AnalyticsService

from src.api.routes_health import health_bp
from src.api.routes_diagnostics import diagnostics_bp
from src.api.routes_web import web_bp
from src.api.routes_auth import auth_bp
from src.api.routes_tenants import tenants_bp
from src.api.routes_patients import patients_bp
from src.api.routes_screenings import screenings_bp
from src.api.routes_analytics import analytics_bp


def create_app(config: Optional[AppConfig] = None) -> Flask:
    """Creates and configures the Flask application instance."""
    if config is None:
        config = AppConfig()

    app = Flask(__name__, static_folder=None)
    app.secret_key = config.secret_key
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = not config.debug
    CORS(app, resources={r"/api/*": {"origins": config.cors_allowed_origins}})

    logger.info("Initializing RetinaLens AI Multi-Tenant Screening Platform...")

    # 1. Database and Schema Initialization
    db = Database(config.db_path)
    db.init_schema()

    # 2. Deep Learning AI & Diagnostic Core (Protected verified EfficientNet-B4)
    model = load_model(config)
    validator = RetinalImageValidator()
    preprocessor = RetinalPreprocessor(config)
    gradcam = GradCAMService(model)
    diagnostic_service = DiagnosticService(
        model=model,
        validator=validator,
        preprocessor=preprocessor,
        gradcam=gradcam,
    )

    # 3. Multi-Tenant Domain Services
    tenant_service = TenantService(db)
    user_service = UserService(db)
    patient_service = PatientService(db)
    screening_service = ScreeningService(
        db=db,
        diagnostic_service=diagnostic_service,
        uploads_dir=config.uploads_dir,
    )
    analytics_service = AnalyticsService(db)

    # 4. Seed Database with Realistic Indian Demo Cohort (only when explicitly enabled)
    if config.seed_demo_data:
        seed_database(
            db=db,
            tenant_service=tenant_service,
            user_service=user_service,
            patient_service=patient_service,
            screening_service=screening_service,
            sample_images_dir=str(config.base_dir / "sample_images"),
        )

    # 5. Store in application context for dependency injection
    app.config["APP_CONFIG"] = config
    app.config["DATABASE"] = db
    app.config["DIAGNOSTIC_SERVICE"] = diagnostic_service
    app.config["TENANT_SERVICE"] = tenant_service
    app.config["USER_SERVICE"] = user_service
    app.config["PATIENT_SERVICE"] = patient_service
    app.config["SCREENING_SERVICE"] = screening_service
    app.config["ANALYTICS_SERVICE"] = analytics_service

    # 6. Register Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(diagnostics_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tenants_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(screenings_bp)
    app.register_blueprint(analytics_bp)

    # 7. Global Domain & HTTP Error Handlers
    @app.errorhandler(RetinaLensException)
    def handle_domain_exception(error: RetinaLensException):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(404)
    def handle_404(error):
        if request.path.startswith("/api/") or (
            request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
        ):
            return jsonify({"error": "Resource not found", "status_code": 404}), 404
        if (config.frontend_dir / "404.html").exists():
            return send_from_directory(str(config.frontend_dir), "404.html"), 404
        return "404 Not Found", 404

    @app.errorhandler(403)
    def handle_403(error):
        if request.path.startswith("/api/") or (
            request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
        ):
            return jsonify({"error": "Access forbidden", "status_code": 403}), 403
        if (config.frontend_dir / "403.html").exists():
            return send_from_directory(str(config.frontend_dir), "403.html"), 403
        return "403 Forbidden", 403

    @app.errorhandler(500)
    def handle_500(error):
        import uuid
        from datetime import datetime
        incident_id = f"AYN-INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        logger.exception("Internal server error [Incident: %s]: %s", incident_id, error)
        if request.path.startswith("/api/") or (
            request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
        ):
            return jsonify({
                "error": "Internal clinical service error",
                "status_code": 500,
                "incident_id": incident_id,
            }), 500
        html_path = config.frontend_dir / "500.html"
        if html_path.exists():
            try:
                content = html_path.read_text(encoding="utf-8")
                rendered = content.replace("AYN-INC-202611-SYS", incident_id).replace("<!-- incident_id -->", incident_id)
                from flask import make_response
                response = make_response(rendered, 500)
                response.headers["Content-Type"] = "text/html; charset=utf-8"
                response.headers["X-Incident-ID"] = incident_id
                return response
            except Exception:
                return send_from_directory(str(config.frontend_dir), "500.html"), 500
        return f"500 Internal Server Error (Incident: {incident_id})", 500

    @app.errorhandler(Exception)
    def handle_unhandled_exception(error: Exception):
        if isinstance(error, HTTPException):
            if error.code == 404:
                return handle_404(error)
            if error.code == 403:
                return handle_403(error)
            if request.path.startswith("/api/") or (
                request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
            ):
                return jsonify({"error": error.description, "status_code": error.code}), error.code
            return error
        return handle_500(error)

    logger.info("RetinaLens AI Multi-Tenant Platform initialized and ready to serve.")
    return app
