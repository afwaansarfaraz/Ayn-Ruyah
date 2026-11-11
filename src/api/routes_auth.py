"""Authentication and hospital workspace session endpoints."""

from flask import Blueprint, request, jsonify, current_app, session
from src.core.logging import logger

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/auth/hospitals", methods=["GET"])
def list_hospitals():
    """Lists registered hospital screening facilities for workspace selection."""
    tenant_service = current_app.config["TENANT_SERVICE"]
    tenants = tenant_service.list_tenants()
    return jsonify({
        "hospitals": [t.to_dict() for t in tenants],
        "count": len(tenants)
    }), 200


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """Authenticates hospital healthcare personnel."""
    if not request.is_json:
        return jsonify({"error": "Request payload must be a JSON object."}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request payload must be a JSON object."}), 400

    username_val = data.get("username")
    password_val = data.get("password")
    if not isinstance(username_val, str) or not isinstance(password_val, str):
        return jsonify({"error": "Username and password must be strings."}), 400

    username = username_val.strip()
    password = password_val

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    tenant_id_val = data.get("tenant_id")
    tenant_id = None
    if tenant_id_val is not None:
        if not isinstance(tenant_id_val, str):
            return jsonify({"error": "Hospital workspace ID must be a string."}), 400
        tenant_id = tenant_id_val.strip() or None

    user_service = current_app.config["USER_SERVICE"]
    tenant_service = current_app.config["TENANT_SERVICE"]

    user = user_service.authenticate(username, password, tenant_id=tenant_id)
    if not user:
        return jsonify({"error": "Invalid username, password, or hospital workspace."}), 401

    tenant = tenant_service.get_tenant(user.tenant_id)
    if not tenant:
        return jsonify({"error": "Hospital workspace associated with user is inactive."}), 403

    session["user_id"] = user.id
    session["tenant_id"] = user.tenant_id
    session["role"] = user.role

    logger.info("User %s logged into hospital workspace %s (%s)", user.username, tenant.name, user.role)

    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(include_sensitive=False),
        "hospital": tenant.to_dict(),
    }), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    """Returns currently authenticated user and active hospital workspace."""
    user_id = session.get("user_id")
    tenant_id = session.get("tenant_id")
    if not user_id or not tenant_id:
        return jsonify({"authenticated": False, "user": None, "hospital": None}), 401

    user_service = current_app.config["USER_SERVICE"]
    tenant_service = current_app.config["TENANT_SERVICE"]

    user = user_service.get_user_by_id(tenant_id, user_id)
    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None, "hospital": None}), 401

    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        session.clear()
        return jsonify({"authenticated": False, "user": None, "hospital": None}), 403

    return jsonify({
        "authenticated": True,
        "user": user.to_dict(include_sensitive=False),
        "hospital": tenant.to_dict(),
    }), 200


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """Clears user session."""
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

