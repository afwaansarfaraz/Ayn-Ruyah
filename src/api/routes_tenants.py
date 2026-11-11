"""Hospital Onboarding and Workspace Management endpoints."""

import hmac
import os
from flask import Blueprint, request, jsonify, current_app, session
from src.api.auth_middleware import require_tenant
from src.core.logging import logger

tenants_bp = Blueprint("tenants", __name__)

ALLOWED_STAFF_ROLES = {"hospital_admin", "ophthalmologist", "screening_operator"}
PERMITTED_TENANT_UPDATE_FIELDS = {
    "name", "city", "state", "address", "contact_email",
    "contact_phone", "registration_number", "logo_url", "tier"
}


@tenants_bp.route("/api/tenants", methods=["POST"])
def register_hospital():
    """Onboards a new independent hospital screening facility. Requires provisioning secret."""
    # Enforce platform-level authorization via provisioning secret
    provisioning_secret = os.getenv("PROVISIONING_SECRET")
    req_secret = request.headers.get("X-Provisioning-Secret")
    is_authorized = False

    if provisioning_secret and req_secret:
        if hmac.compare_digest(
            req_secret.strip().encode("utf-8"),
            provisioning_secret.strip().encode("utf-8"),
        ):
            is_authorized = True

    if not is_authorized:
        return jsonify({
            "error": "Unauthorized to register hospital workspaces. Provide valid X-Provisioning-Secret header."
        }), 403

    data = request.get_json() or {}
    required = ["id", "name", "city", "state", "address", "contact_email", "contact_phone"]
    for r in required:
        if not data.get(r):
            return jsonify({"error": f"Missing required field: {r}"}), 400

    tenant_service = current_app.config["TENANT_SERVICE"]
    user_service = current_app.config["USER_SERVICE"]

    # Pre-validate admin account data if provided
    admin_data = data.get("admin")
    if admin_data:
        if not isinstance(admin_data, dict):
            return jsonify({"error": "Admin field must be an object."}), 400
        admin_uname = str(admin_data.get("username") or "").strip()
        admin_pwd = str(admin_data.get("password") or "")
        if not admin_uname:
            return jsonify({"error": "Admin username is required when configuring administrator."}), 400
        if not admin_pwd or len(admin_pwd) < 6:
            return jsonify({"error": "Admin password must be at least 6 characters long."}), 400

    try:
        tenant = tenant_service.create_tenant(
            tenant_id=data["id"],
            name=data["name"],
            city=data["city"],
            state=data["state"],
            address=data["address"],
            contact_email=data["contact_email"],
            contact_phone=data["contact_phone"],
            registration_number=data.get("registration_number"),
            logo_url=data.get("logo_url"),
            tier=data.get("tier", "Standard"),
        )

        # Create primary administrator account if provided
        if admin_data:
            try:
                user_service.create_user(
                    tenant_id=tenant.id,
                    username=admin_uname,
                    password=admin_pwd,
                    full_name=admin_data.get("full_name", f"{tenant.name} Administrator"),
                    role="hospital_admin",
                    email=admin_data.get("email", tenant.contact_email),
                    phone=admin_data.get("phone", tenant.contact_phone),
                    qualification=admin_data.get("qualification", "Hospital Administrator"),
                )
            except Exception as admin_err:
                with tenant_service.db.session() as conn:
                    conn.execute("DELETE FROM tenants WHERE id = ?", (tenant.id,))
                logger.error("Failed to create admin user for tenant %s, rolled back tenant: %s", tenant.id, admin_err)
                raise

        return jsonify({
            "message": "Hospital workspace registered successfully",
            "hospital": tenant.to_dict()
        }), 201

    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as exc:
        logger.error("Error registering hospital: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to onboard hospital workspace."}), 500


@tenants_bp.route("/api/tenants/<tenant_id>", methods=["GET"])
@require_tenant
def get_hospital_profile(tenant_id: str):
    """Retrieves hospital profile and branding configuration for authenticated workspace."""
    tenant_service = current_app.config["TENANT_SERVICE"]
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": f"Hospital '{tenant_id}' not found."}), 404
    return jsonify(tenant.to_dict()), 200


@tenants_bp.route("/api/tenants/<tenant_id>", methods=["PUT"])
@require_tenant(roles=["hospital_admin"])
def update_hospital_profile(tenant_id: str):
    """Updates hospital profile and contact details. Rejects changes to identifier."""
    data = request.get_json() or {}
    if data.get("id") and data.get("id") != tenant_id:
        return jsonify({"error": "Modifying hospital workspace identifier is not permitted."}), 400

    sanitized_updates = {
        k: v for k, v in data.items()
        if k in PERMITTED_TENANT_UPDATE_FIELDS
    }

    tenant_service = current_app.config["TENANT_SERVICE"]
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": f"Hospital '{tenant_id}' not found."}), 404

    updated = tenant_service.update_tenant(tenant_id, sanitized_updates)
    return jsonify({
        "message": "Hospital profile updated successfully",
        "hospital": updated.to_dict()
    }), 200


@tenants_bp.route("/api/tenants/<tenant_id>/users", methods=["GET"])
@require_tenant
def list_hospital_staff(tenant_id: str):
    """Lists healthcare staff members authorized for this hospital workspace."""
    user_service = current_app.config["USER_SERVICE"]
    role = request.args.get("role")
    users = user_service.list_users_for_tenant(tenant_id, role=role)
    return jsonify([u.to_dict(include_sensitive=False) for u in users]), 200


@tenants_bp.route("/api/tenants/<tenant_id>/users", methods=["POST"])
@require_tenant(roles=["hospital_admin"])
def add_hospital_staff(tenant_id: str):
    """Adds a new doctor, administrator, or screening operator to the hospital."""
    tenant_service = current_app.config["TENANT_SERVICE"]
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant:
        return jsonify({"error": f"Hospital '{tenant_id}' not found."}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    required = ["username", "password", "full_name", "role", "email"]
    for r in required:
        val = data.get(r)
        if val is None or not isinstance(val, str) or not val.strip():
            return jsonify({"error": f"Missing or invalid required string field: {r}"}), 400

    role = data["role"].strip()
    if role not in ALLOWED_STAFF_ROLES:
        return jsonify({
            "error": f"Invalid role '{role}'. Allowed roles are: {', '.join(sorted(ALLOWED_STAFF_ROLES))}"
        }), 400

    phone = data.get("phone")
    if phone is not None and not isinstance(phone, str):
        return jsonify({"error": "Field 'phone' must be a string."}), 400
    phone_str = phone.strip() if isinstance(phone, str) else None

    qualification = data.get("qualification")
    if qualification is not None and not isinstance(qualification, str):
        return jsonify({"error": "Field 'qualification' must be a string."}), 400
    qual_str = qualification.strip() if isinstance(qualification, str) else None

    user_service = current_app.config["USER_SERVICE"]
    try:
        user = user_service.create_user(
            tenant_id=tenant_id,
            username=data["username"].strip(),
            password=data["password"],
            full_name=data["full_name"].strip(),
            role=role,
            email=data["email"].strip(),
            phone=phone_str,
            qualification=qual_str,
        )
        return jsonify({
            "message": "Staff member created successfully",
            "user": user.to_dict(include_sensitive=False)
        }), 201
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as exc:
        logger.error("Failed adding staff member: %s", exc)
        return jsonify({"error": "Failed to add staff member."}), 500
