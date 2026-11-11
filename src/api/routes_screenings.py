"""AI Retinal Screening session and image analysis endpoints."""

from flask import Blueprint, request, jsonify, current_app, session
from src.api.auth_middleware import require_tenant
from src.core.exceptions import InvalidRetinalImageError, PatientNotFoundError
from src.core.logging import logger

screenings_bp = Blueprint("screenings", __name__)


@screenings_bp.route("/api/screenings", methods=["GET"])
@require_tenant
def list_screenings(tenant_id: str):
    """Lists retinal fundus screenings for the current hospital."""
    screening_service = current_app.config["SCREENING_SERVICE"]

    patient_id = request.args.get("patient_id")
    status = request.args.get("status")
    grade_str = request.args.get("grade")
    grade = int(grade_str) if grade_str is not None and grade_str.isdigit() else None
    limit_param = request.args.get("limit", default=50, type=int)
    offset_param = request.args.get("offset", default=0, type=int)
    limit = 50 if (limit_param is None or limit_param < 1) else min(limit_param, 100)
    offset = 0 if (offset_param is None or offset_param < 0) else offset_param

    screenings, total = screening_service.list_screenings(
        tenant_id=tenant_id,
        patient_id=patient_id,
        grade=grade,
        status=status,
        limit=limit,
        offset=offset,
    )

    return jsonify({
        "screenings": [s.to_dict() for s in screenings],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@screenings_bp.route("/api/screenings", methods=["POST"])
@require_tenant
def execute_screening(tenant_id: str):
    """
    Uploads a fundus scan, runs real EfficientNet-B4 inference + Grad-CAM,
    and persists the screening session in the hospital database.
    """
    if "image" not in request.files:
        return jsonify({"error": "No retinal fundus image provided."}), 400

    patient_id = request.form.get("patient_id")
    if not patient_id:
        return jsonify({"error": "patient_id is required for screening session."}), 400

    eye = request.form.get("eye", "Left Eye (OS)")
    notes = request.form.get("notes")
    operator_id = session.get("user_id") or request.form.get("operator_id")
    doctor_id = request.form.get("doctor_id")

    if doctor_id:
        user_service = current_app.config["USER_SERVICE"]
        doc = user_service.get_user_by_id(tenant_id, doctor_id)
        if not doc:
            return jsonify({"error": "Invalid doctor_id: doctor does not exist in this hospital workspace."}), 400

    image_file = request.files["image"]
    image_bytes = image_file.read()
    if not image_bytes:
        return jsonify({"error": "Empty image file received."}), 400

    screening_service = current_app.config["SCREENING_SERVICE"]

    try:
        screening = screening_service.execute_and_save_screening(
            tenant_id=tenant_id,
            patient_id=patient_id,
            image_bytes=image_bytes,
            eye=eye,
            operator_id=operator_id,
            doctor_id=doctor_id,
            notes=notes,
        )

        return jsonify({
            "message": "AI Screening completed and saved successfully",
            "screening": screening.to_dict()
        }), 201

    except PatientNotFoundError as nf_err:
        logger.warning("Patient not found for screening: %s", nf_err.message)
        return jsonify({"error": nf_err.message}), 404

    except InvalidRetinalImageError as val_err:
        logger.warning("Screening rejected image: %s", val_err.message)
        return jsonify({"error": val_err.message}), 400

    except Exception as exc:
        logger.error("Screening failure: %s", exc, exc_info=True)
        return jsonify({"error": "Internal screening error."}), 500


@screenings_bp.route("/api/screenings/<screening_id>", methods=["GET"])
@require_tenant
def get_screening_detail(tenant_id: str, screening_id: str):
    """Retrieves full details of a screening session including heatmap and probabilities."""
    screening_service = current_app.config["SCREENING_SERVICE"]
    screening = screening_service.get_screening(tenant_id, screening_id)
    if not screening:
        return jsonify({"error": f"Screening '{screening_id}' not found in this hospital workspace."}), 404

    return jsonify(screening.to_dict()), 200

