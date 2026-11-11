"""Patient management service with strict hospital-level tenant isolation."""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid

from src.database.connection import Database
from src.database.models import Patient
from src.core.exceptions import DuplicatePatientError
from src.core.logging import logger


class PatientService:
    """Manages diabetic retinopathy screening patient cohort and history."""

    def __init__(self, db: Database):
        self.db = db

    def register_patient(
        self,
        tenant_id: str,
        first_name: str,
        last_name: str,
        gender: str,
        dob: str,
        age: int,
        phone: str,
        address: str,
        city: str,
        state: str,
        diabetes_type: str,
        diabetes_duration_years: float,
        email: Optional[str] = None,
        pincode: Optional[str] = None,
        avatar_url: Optional[str] = None,
        hba1c: Optional[float] = None,
        insulin_dependent: int = 0,
        hypertension: int = 0,
        smoker: int = 0,
        assigned_doctor_id: Optional[str] = None,
        is_minor: int = 0,
        guardian_name: Optional[str] = None,
        guardian_relation: Optional[str] = None,
        guardian_phone: Optional[str] = None,
        clinical_notes: Optional[str] = None,
        is_demo: int = 0,
        patient_id: Optional[str] = None,
    ) -> Patient:
        """Registers a new screening patient under the hospital workspace."""
        pid = patient_id or f"PAT-IND-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.utcnow().isoformat()

        # Minor automatic calculation/guard
        if age < 18:
            is_minor = 1

        clean_first = first_name.strip()
        clean_last = last_name.strip()
        clean_phone = phone.strip()

        with self.db.session() as conn:
            # Prevent duplicate patient registration within the same hospital workspace
            existing = conn.execute(
                """
                SELECT id FROM patients
                WHERE tenant_id = ?
                  AND LOWER(first_name) = ?
                  AND LOWER(last_name) = ?
                  AND (dob = ? OR (phone != '' AND phone = ?))
                """,
                (tenant_id, clean_first.lower(), clean_last.lower(), dob, clean_phone)
            ).fetchone()
            if existing:
                raise DuplicatePatientError(
                    f"Patient '{clean_first} {clean_last}' already exists in this hospital workspace (ID: {existing['id']})."
                )

            conn.execute(
                """
                INSERT INTO patients (
                    id, tenant_id, first_name, last_name, gender, dob, age,
                    phone, email, address, city, state, pincode, avatar_url,
                    diabetes_type, diabetes_duration_years, hba1c, insulin_dependent,
                    hypertension, smoker, assigned_doctor_id, is_minor,
                    guardian_name, guardian_relation, guardian_phone,
                    clinical_notes, is_demo, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid, tenant_id, first_name.strip(), last_name.strip(), gender,
                    dob, age, phone.strip(), email, address.strip(), city.strip(),
                    state.strip(), pincode, avatar_url, diabetes_type,
                    diabetes_duration_years, hba1c, insulin_dependent, hypertension,
                    smoker, assigned_doctor_id, is_minor, guardian_name,
                    guardian_relation, guardian_phone, clinical_notes, is_demo, now
                )
            )

        logger.info("Registered patient %s under tenant %s", pid, tenant_id)
        return self.get_patient(tenant_id, pid)

    def get_patient(self, tenant_id: str, patient_id: str) -> Optional[Patient]:
        """Retrieves a patient record strictly validating tenant ownership."""
        with self.db.session() as conn:
            row = conn.execute(
                "SELECT * FROM patients WHERE id = ? AND tenant_id = ?",
                (patient_id, tenant_id)
            ).fetchone()
            return self._row_to_patient(row) if row else None

    def list_patients(
        self,
        tenant_id: str,
        search_query: Optional[str] = None,
        diabetes_type: Optional[str] = None,
        is_minor: Optional[bool] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Patient], int]:
        """Lists patients for a tenant with search, filtering, and total count."""
        with self.db.session() as conn:
            conditions = ["tenant_id = ?"]
            params: List[Any] = [tenant_id]

            if search_query:
                q = f"%{search_query.strip().lower()}%"
                conditions.append(
                    "(LOWER(first_name) LIKE ? OR LOWER(last_name) LIKE ? OR LOWER(id) LIKE ? OR phone LIKE ?)"
                )
                params.extend([q, q, q, q])

            if diabetes_type:
                conditions.append("diabetes_type = ?")
                params.append(diabetes_type)

            if is_minor is not None:
                conditions.append("is_minor = ?")
                params.append(1 if is_minor else 0)

            # Calculate current age from dob (falling back to stored age if dob is unavailable)
            current_age_sql = "COALESCE((strftime('%Y', 'now') - strftime('%Y', dob)) - (strftime('%m-%d', 'now') < strftime('%m-%d', dob)), age)"

            if min_age is not None:
                conditions.append(f"{current_age_sql} >= ?")
                params.append(min_age)

            if max_age is not None:
                conditions.append(f"{current_age_sql} <= ?")
                params.append(max_age)

            where_clause = " AND ".join(conditions)

            # Get total count
            count_row = conn.execute(
                f"SELECT COUNT(*) as total FROM patients WHERE {where_clause}",
                params
            ).fetchone()
            total = count_row["total"] if count_row else 0

            # Get page
            query = f"SELECT * FROM patients WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
            page_params = params + [limit, offset]
            rows = conn.execute(query, page_params).fetchall()

            return [self._row_to_patient(r) for r in rows], total

    def update_patient(self, tenant_id: str, patient_id: str, updates: Dict[str, Any]) -> Optional[Patient]:
        """Updates patient record ensuring tenant isolation."""
        required_schema_fields = {
            "first_name", "last_name", "gender", "dob", "age",
            "phone", "address", "city", "state", "diabetes_type", "diabetes_duration_years"
        }
        allowed_fields = [
            "first_name", "last_name", "gender", "dob", "age", "phone", "email",
            "address", "city", "state", "pincode", "avatar_url", "diabetes_type",
            "diabetes_duration_years", "hba1c", "insulin_dependent", "hypertension",
            "smoker", "assigned_doctor_id", "guardian_name", "guardian_relation",
            "guardian_phone", "clinical_notes"
        ]

        # Validate required fields are not explicitly set to None
        for field, val in updates.items():
            if field in required_schema_fields and val is None:
                raise ValueError(f"Required patient field '{field}' cannot be set to None.")

        set_clauses = []
        values = []

        for field, val in updates.items():
            if field == "age":
                age_int = int(val)
                is_minor = 1 if age_int < 18 else 0
                set_clauses.append("age = ?")
                values.append(age_int)
                set_clauses.append("is_minor = ?")
                values.append(is_minor)
            elif field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(val)

        if not set_clauses:
            return self.get_patient(tenant_id, patient_id)

        values.extend([patient_id, tenant_id])
        with self.db.session() as conn:
            cursor = conn.execute(
                f"UPDATE patients SET {', '.join(set_clauses)} WHERE id = ? AND tenant_id = ?",
                values
            )
            if cursor.rowcount == 0:
                return None

        return self.get_patient(tenant_id, patient_id)

    @staticmethod
    def _row_to_patient(row: Any) -> Patient:
        return Patient(
            id=row["id"],
            tenant_id=row["tenant_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            gender=row["gender"],
            dob=row["dob"],
            age=row["age"],
            phone=row["phone"],
            address=row["address"],
            city=row["city"],
            state=row["state"],
            diabetes_type=row["diabetes_type"],
            diabetes_duration_years=row["diabetes_duration_years"],
            email=row["email"],
            pincode=row["pincode"],
            avatar_url=row["avatar_url"],
            hba1c=row["hba1c"],
            insulin_dependent=row["insulin_dependent"],
            hypertension=row["hypertension"],
            smoker=row["smoker"],
            assigned_doctor_id=row["assigned_doctor_id"],
            is_minor=row["is_minor"],
            guardian_name=row["guardian_name"],
            guardian_relation=row["guardian_relation"],
            guardian_phone=row["guardian_phone"],
            clinical_notes=row["clinical_notes"],
            is_demo=row["is_demo"],
            created_at=row["created_at"],
        )

