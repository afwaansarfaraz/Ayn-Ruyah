"""Patient directory and clinical profile management endpoints."""

from flask import Blueprint, request, jsonify, current_app
from src.api.auth_middleware import require_tenant
from src.core.exceptions import DuplicatePatientError
from src.core.logging import logger

patients_bp = Blueprint("patients", __name__)


@patients_bp.route("/api/patients", methods=["GET"])
@require_tenant
def list_patients(tenant_id: str):
    """Lists screening patients belonging strictly to the authorized hospital."""
    patient_service = current_app.config["PATIENT_SERVICE"]
    search = request.args.get("search")
    diabetes_type = request.args.get("diabetes_type")
    is_minor_str = request.args.get("is_minor")
    is_minor = None
    if is_minor_str is not None:
        is_minor = is_minor_str.lower() in ("true", "1", "yes")

    min_age = request.args.get("min_age", type=int)
    max_age = request.args.get("max_age", type=int)

    limit_param = request.args.get("limit", default=100, type=int)
    offset_param = request.args.get("offset", default=0, type=int)
    limit = 100 if (limit_param is None or limit_param < 1) else min(limit_param, 200)
    offset = 0 if (offset_param is None or offset_param < 0) else offset_param

    patients, total = patient_service.list_patients(
        tenant_id=tenant_id,
        search_query=search,
        diabetes_type=diabetes_type,
        is_minor=is_minor,
        min_age=min_age,
        max_age=max_age,
        limit=limit,
        offset=offset,
    )

    return jsonify({
        "patients": [p.to_dict() for p in patients],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@patients_bp.route("/api/patients", methods=["POST"])
@require_tenant
def register_patient(tenant_id: str):
    """Registers a new screening patient under the hospital workspace."""
    data = request.get_json() or {}
    required = [
        "first_name", "last_name", "gender", "dob", "age", "phone",
        "address", "city", "state", "diabetes_type", "diabetes_duration_years"
    ]
    for r in required:
        if r not in data or data[r] is None or str(data[r]).strip() == "":
            return jsonify({"error": f"Missing required field: {r}"}), 400

    patient_service = current_app.config["PATIENT_SERVICE"]
    user_service = current_app.config["USER_SERVICE"]
    try:
        age = int(data["age"])
        duration = float(data["diabetes_duration_years"])
        hba1c = float(data["hba1c"]) if data.get("hba1c") is not None else None

        assigned_doctor_id = data.get("assigned_doctor_id")
        if assigned_doctor_id:
            doctor = user_service.get_user_by_id(tenant_id, assigned_doctor_id)
            if not doctor or doctor.role != "ophthalmologist":
                return jsonify({"error": "Invalid assigned doctor: must be an active ophthalmologist in this hospital workspace."}), 400

        # Build synthetic avatar if not supplied
        avatar_url = data.get("avatar_url")
        if not avatar_url:
            from src.database.seeds import get_avatar
            avatar_url = get_avatar(f"{data['first_name']}_{data['last_name']}", data["gender"])

        patient = patient_service.register_patient(
            tenant_id=tenant_id,
            first_name=str(data["first_name"]),
            last_name=str(data["last_name"]),
            gender=str(data["gender"]),
            dob=str(data["dob"]),
            age=age,
            phone=str(data["phone"]),
            email=data.get("email"),
            address=str(data["address"]),
            city=str(data["city"]),
            state=str(data["state"]),
            pincode=data.get("pincode"),
            avatar_url=avatar_url,
            diabetes_type=str(data["diabetes_type"]),
            diabetes_duration_years=duration,
            hba1c=hba1c,
            insulin_dependent=1 if data.get("insulin_dependent") else 0,
            hypertension=1 if data.get("hypertension") else 0,
            smoker=1 if data.get("smoker") else 0,
            assigned_doctor_id=data.get("assigned_doctor_id"),
            is_minor=1 if (data.get("is_minor") or age < 18) else 0,
            guardian_name=data.get("guardian_name"),
            guardian_relation=data.get("guardian_relation"),
            guardian_phone=data.get("guardian_phone"),
            clinical_notes=data.get("clinical_notes"),
            is_demo=0,
        )

        return jsonify({
            "message": "Patient registered successfully",
            "patient": patient.to_dict()
        }), 201

    except DuplicatePatientError as dup_err:
        logger.warning("Duplicate patient registration attempt: %s", dup_err.message)
        return jsonify({"error": dup_err.message}), 409

    except (ValueError, TypeError) as exc:
        logger.warning("Invalid patient registration payload: %s", exc)
        return jsonify({"error": "Invalid patient registration payload."}), 400

    except Exception as exc:
        logger.error("Error registering patient: %s", exc, exc_info=True)
        return jsonify({"error": "Failed to register patient."}), 500


@patients_bp.route("/api/patients/<patient_id>", methods=["GET"])
@require_tenant
def get_patient_details(tenant_id: str, patient_id: str):
    """Retrieves patient profile with tenant isolation enforcement."""
    patient_service = current_app.config["PATIENT_SERVICE"]
    patient = patient_service.get_patient(tenant_id, patient_id)
    if not patient:
        return jsonify({"error": f"Patient '{patient_id}' not found in this hospital workspace."}), 404

    return jsonify(patient.to_dict()), 200


@patients_bp.route("/api/patients/<patient_id>", methods=["PUT"])
@require_tenant
def update_patient_details(tenant_id: str, patient_id: str):
    """Updates patient profile within tenant workspace."""
    data = request.get_json() or {}
    assigned_doctor_id = data.get("assigned_doctor_id")
    if assigned_doctor_id:
        user_service = current_app.config["USER_SERVICE"]
        doctor = user_service.get_user_by_id(tenant_id, assigned_doctor_id)
        if not doctor or doctor.role != "ophthalmologist":
            return jsonify({"error": "Invalid assigned doctor: must be an active ophthalmologist in this hospital workspace."}), 400

    patient_service = current_app.config["PATIENT_SERVICE"]
    updated = patient_service.update_patient(tenant_id, patient_id, data)
    if not updated:
        return jsonify({"error": f"Patient '{patient_id}' not found."}), 404

    return jsonify({
        "message": "Patient profile updated successfully",
        "patient": updated.to_dict()
    }), 200


@patients_bp.route("/api/patients/<patient_id>/screenings", methods=["GET"])
@require_tenant
def get_patient_screenings(tenant_id: str, patient_id: str):
    """Retrieves all historical AI retinal screening sessions for a patient."""
    patient_service = current_app.config["PATIENT_SERVICE"]
    patient = patient_service.get_patient(tenant_id, patient_id)
    if not patient:
        return jsonify({"error": f"Patient '{patient_id}' not found in this hospital workspace."}), 404

    screening_service = current_app.config["SCREENING_SERVICE"]
    screenings, total = screening_service.list_screenings(
        tenant_id=tenant_id,
        patient_id=patient_id,
        limit=50
    )

    return jsonify({
        "patient_id": patient_id,
        "screenings": [s.to_dict() for s in screenings],
        "total": total
    }), 200

