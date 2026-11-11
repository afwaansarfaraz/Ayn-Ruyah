"""AI Retinal Screening service coordinating deep learning inference and persistence."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import json
import uuid
import os
import base64
from pathlib import Path

from src.database.connection import Database
from src.database.models import Screening
from src.services.diagnostic_service import DiagnosticService
from src.core.exceptions import InvalidRetinalImageError, PatientNotFoundError
from src.core.logging import logger


class ScreeningService:
    """Manages AI retinal screenings, persisting results with strict tenant isolation."""

    def __init__(self, db: Database, diagnostic_service: DiagnosticService, uploads_dir: Path):
        self.db = db
        self.diagnostic_service = diagnostic_service
        self.uploads_dir = Path(uploads_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def execute_and_save_screening(
        self,
        tenant_id: str,
        patient_id: str,
        image_bytes: bytes,
        eye: str = "Left Eye (OS)",
        operator_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Screening:
        """Executes real EfficientNet-B4 AI inference + Grad-CAM, saves result to database."""
        # 1. Verify patient exists and belongs to this tenant
        with self.db.session() as conn:
            patient = conn.execute(
                "SELECT id FROM patients WHERE id = ? AND tenant_id = ?",
                (patient_id, tenant_id)
            ).fetchone()
            if not patient:
                raise PatientNotFoundError(f"Patient '{patient_id}' not found under hospital '{tenant_id}'.")

        # 2. Run real AI Diagnostic pipeline
        result = self.diagnostic_service.analyze_image_bytes(image_bytes)

        screening_id = f"SCR-IND-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.utcnow().isoformat()

        # Determine clinical workflow status
        if result.grade >= 3:
            status = "Urgent Specialist Review"
        elif result.grade in (1, 2):
            status = "Referred"
        else:
            status = "Completed"

        # 3. Store original image and heatmap under self.uploads_dir with relative paths
        if image_bytes.startswith(b"\x89PNG"):
            orig_ext = ".png"
        else:
            orig_ext = ".jpg"

        tenant_upload_dir = self.uploads_dir / tenant_id
        tenant_upload_dir.mkdir(parents=True, exist_ok=True)

        orig_filename = f"{screening_id}_orig{orig_ext}"
        (tenant_upload_dir / orig_filename).write_bytes(image_bytes)
        rel_orig_path = f"/uploads/{tenant_id}/{orig_filename}"

        rel_heatmap_path = None
        if result.heatmap:
            if "base64," in result.heatmap:
                b64_data = result.heatmap.split("base64,")[1]
                heatmap_bytes = base64.b64decode(b64_data)
                heatmap_filename = f"{screening_id}_heatmap.png"
                (tenant_upload_dir / heatmap_filename).write_bytes(heatmap_bytes)
                rel_heatmap_path = f"/uploads/{tenant_id}/{heatmap_filename}"
            else:
                rel_heatmap_path = result.heatmap

        # 4. Persist record in database
        with self.db.session() as conn:
            conn.execute(
                """
                INSERT INTO screenings (
                    id, tenant_id, patient_id, operator_id, doctor_id,
                    eye, grade, diagnosis, confidence, severity,
                    probabilities_json, recommendation, original_image_path,
                    heatmap_image_path, notes, status, is_demo, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    screening_id, tenant_id, patient_id, operator_id, doctor_id,
                    eye, result.grade, result.result, result.confidence, result.severity,
                    json.dumps(result.probabilities), result.recommendation,
                    rel_orig_path, rel_heatmap_path, notes, status,
                    1 if getattr(result, "demo_mode", False) else 0, now
                )
            )

        logger.info(
            "Screening %s completed for patient %s under tenant %s: Grade %d (%s, %.1f%%)",
            screening_id, patient_id, tenant_id, result.grade, result.result, result.confidence
        )

        return self.get_screening(tenant_id, screening_id)

    def create_demo_screening(
        self,
        tenant_id: str,
        patient_id: str,
        eye: str,
        grade: int,
        diagnosis: str,
        confidence: float,
        severity: str,
        probabilities: Dict[str, float],
        recommendation: str,
        original_image_path: Optional[str] = None,
        heatmap_image_path: Optional[str] = None,
        operator_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        status: str = "Completed",
        created_at: Optional[str] = None,
        screening_id: Optional[str] = None,
    ) -> Screening:
        """Saves a synthetic historical demo screening record clearly flagged with is_demo=1."""
        sid = screening_id or f"SCR-DEMO-{uuid.uuid4().hex[:6].upper()}"
        now = created_at or datetime.utcnow().isoformat()

        with self.db.session() as conn:
            conn.execute(
                """
                INSERT INTO screenings (
                    id, tenant_id, patient_id, operator_id, doctor_id,
                    eye, grade, diagnosis, confidence, severity,
                    probabilities_json, recommendation, original_image_path,
                    heatmap_image_path, notes, status, is_demo, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    sid, tenant_id, patient_id, operator_id, doctor_id,
                    eye, grade, diagnosis, confidence, severity,
                    json.dumps(probabilities), recommendation,
                    original_image_path, heatmap_image_path,
                    "[DEMO DATA - Synthetic Screening Record]",
                    status, now
                )
            )

        return self.get_screening(tenant_id, sid)

    def _resolve_image_to_data_url(self, path_str: Optional[str]) -> Optional[str]:
        if not path_str:
            return None
        if path_str.startswith("data:") or path_str.startswith("http"):
            return path_str
        file_path = self.uploads_dir / path_str
        if not file_path.exists():
            return path_str
        try:
            data = file_path.read_bytes()
            mime = "image/png" if data.startswith(b"\x89PNG") else "image/jpeg"
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except Exception as err:
            logger.warning("Could not read uploaded image %s: %s", file_path, err)
            return path_str

    def get_screening(self, tenant_id: str, screening_id: str) -> Optional[Screening]:
        """Retrieves a screening record strictly enforcing tenant isolation and resolving full images."""
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT * FROM screenings WHERE id = ? AND tenant_id = ?",
                (screening_id, tenant_id)
            ).fetchone()
            return self._row_to_screening(row, load_images=True) if row else None

    def list_screenings(
        self,
        tenant_id: str,
        patient_id: Optional[str] = None,
        grade: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Screening], int]:
        """Lists screenings for a tenant with filters and pagination without eagerly loading large blobs."""
        with self.db.session() as conn:
            conditions = ["s.tenant_id = ?"]
            params: List[Any] = [tenant_id]

            if patient_id:
                conditions.append("s.patient_id = ?")
                params.append(patient_id)

            if grade is not None:
                conditions.append("s.grade = ?")
                params.append(grade)

            if status:
                conditions.append("s.status = ?")
                params.append(status)

            where_clause = " AND ".join(conditions)

            count_row = conn.execute(
                f"SELECT COUNT(*) as total FROM screenings s WHERE {where_clause}",
                params
            ).fetchone()
            total = count_row["total"] if count_row else 0

            query = f"""
                SELECT s.*, p.first_name as pat_first, p.last_name as pat_last
                FROM screenings s
                LEFT JOIN patients p ON s.patient_id = p.id
                WHERE {where_clause}
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, params + [limit, offset]).fetchall()

            screenings = []
            for r in rows:
                sc = self._row_to_screening(r, load_images=False)
                if "pat_first" in r.keys() and r["pat_first"]:
                    sc.patient_name = f"{r['pat_first']} {r['pat_last'] or ''}".strip()
                screenings.append(sc)

            return screenings, total

    def _row_to_screening(self, row: Any, load_images: bool = False) -> Screening:
        try:
            probs = json.loads(row["probabilities_json"])
        except Exception:
            probs = {}

        orig_path = row["original_image_path"]
        heatmap_path = row["heatmap_image_path"]

        if load_images:
            orig_path = self._resolve_image_to_data_url(orig_path)
            heatmap_path = self._resolve_image_to_data_url(heatmap_path)

        return Screening(
            id=row["id"],
            tenant_id=row["tenant_id"],
            patient_id=row["patient_id"],
            eye=row["eye"],
            grade=row["grade"],
            diagnosis=row["diagnosis"],
            confidence=row["confidence"],
            severity=row["severity"],
            probabilities=probs,
            recommendation=row["recommendation"],
            operator_id=row["operator_id"],
            doctor_id=row["doctor_id"],
            original_image_path=orig_path,
            heatmap_image_path=heatmap_path,
            notes=row["notes"],
            status=row["status"],
            is_demo=row["is_demo"],
            created_at=row["created_at"],
        )
