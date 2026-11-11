"""Web interface and static asset serving endpoints."""

import os
from flask import Blueprint, send_from_directory, current_app, abort
from src.api.auth_middleware import require_tenant

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def index():
    """Serves the main application single-page interface."""
    config = current_app.config["APP_CONFIG"]
    resp = send_from_directory(str(config.frontend_dir), "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

@web_bp.route("/404")
def page_404():
    """Explicitly preview or serve the branded 404 page."""
    config = current_app.config["APP_CONFIG"]
    return send_from_directory(str(config.frontend_dir), "404.html"), 404

@web_bp.route("/403")
def page_403():
    """Explicitly preview or serve the branded 403 page."""
    config = current_app.config["APP_CONFIG"]
    return send_from_directory(str(config.frontend_dir), "403.html"), 403

@web_bp.route("/500")
def page_500():
    """Explicitly preview or serve the branded 500 page."""
    import uuid
    from datetime import datetime
    from flask import make_response
    config = current_app.config["APP_CONFIG"]
    html_path = config.frontend_dir / "500.html"
    incident_id = f"AYN-INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    if html_path.exists():
        try:
            content = html_path.read_text(encoding="utf-8")
            rendered = content.replace("AYN-INC-202611-SYS", incident_id).replace("<!-- incident_id -->", incident_id)
            resp = make_response(rendered, 500)
            resp.headers["Content-Type"] = "text/html; charset=utf-8"
            resp.headers["X-Incident-ID"] = incident_id
            return resp
        except Exception:
            pass
    return send_from_directory(str(config.frontend_dir), "500.html"), 500

@web_bp.route("/uploads/<tenant_id>/<path:filename>")
@require_tenant
def serve_tenant_upload(tenant_id: str, filename: str):
    """Securely serves uploaded scans and Grad-CAM heatmaps for authenticated tenant."""
    config = current_app.config["APP_CONFIG"]
    target = config.uploads_dir / tenant_id / filename
    if target.exists() and target.is_file():
        return send_from_directory(str(config.uploads_dir / tenant_id), filename)
    abort(404)


@web_bp.route("/<path:filename>")
def serve_static(filename):
    """Serves static files from frontend, sample_images, or images directories."""
    config = current_app.config["APP_CONFIG"]

    # 1. Check frontend directory (css, js, html, assets)
    frontend_target = config.frontend_dir / filename
    if frontend_target.exists() and frontend_target.is_file():
        resp = send_from_directory(str(config.frontend_dir), filename)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

    # 2. Check sample_images directory
    clean_sample = filename
    if clean_sample.startswith("sample_images/"):
        clean_sample = clean_sample[len("sample_images/"):]
    sample_target = config.base_dir / "sample_images" / clean_sample
    if sample_target.exists() and sample_target.is_file():
        return send_from_directory(str(config.base_dir / "sample_images"), clean_sample)

    # 3. Check images directory
    clean_img = filename
    if clean_img.startswith("images/"):
        clean_img = clean_img[len("images/"):]
    img_target = config.base_dir / "images" / clean_img
    if img_target.exists() and img_target.is_file():
        return send_from_directory(str(config.base_dir / "images"), clean_img)

    abort(404)


