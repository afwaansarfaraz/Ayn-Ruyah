"""Domain data models and schemas for multi-tenant Diabetic Retinopathy platform."""

from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
import json


@dataclass
class Tenant:
    """Hospital or Retinal Screening Facility."""
    id: str
    name: str
    city: str
    state: str
    address: str
    contact_email: str
    contact_phone: str
    registration_number: Optional[str] = None
    logo_url: Optional[str] = None
    tier: str = "Standard"
    created_at: str = ""
    is_active: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class User:
    """Healthcare staff member with role-based access."""
    id: str
    tenant_id: str
    username: str
    password_hash: str
    full_name: str
    role: str  # 'hospital_admin', 'ophthalmologist', 'screening_operator'
    email: str
    phone: Optional[str] = None
    qualification: Optional[str] = None
    created_at: str = ""
    is_active: int = 1

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        if not include_sensitive:
            data.pop("password_hash", None)
        return data


@dataclass
class Patient:
    """Diabetic Retinopathy screening cohort patient."""
    id: str
    tenant_id: str
    first_name: str
    last_name: str
    gender: str
    dob: str
    age: int
    phone: str
    address: str
    city: str
    state: str
    diabetes_type: str  # 'Type 1', 'Type 2', 'Gestational', 'Pre-diabetes'
    diabetes_duration_years: float
    email: Optional[str] = None
    pincode: Optional[str] = None
    avatar_url: Optional[str] = None
    hba1c: Optional[float] = None
    insulin_dependent: int = 0
    hypertension: int = 0
    smoker: int = 0
    assigned_doctor_id: Optional[str] = None
    is_minor: int = 0
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    guardian_phone: Optional[str] = None
    clinical_notes: Optional[str] = None
    is_demo: int = 0
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Screening:
    """AI Retinal Screening session result."""
    id: str
    tenant_id: str
    patient_id: str
    eye: str
    grade: int
    diagnosis: str
    confidence: float
    severity: str
    probabilities: Dict[str, float]
    recommendation: str
    operator_id: Optional[str] = None
    doctor_id: Optional[str] = None
    original_image_path: Optional[str] = None
    heatmap_image_path: Optional[str] = None
    notes: Optional[str] = None
    status: str = "Completed"
    is_demo: int = 0
    created_at: str = ""
    patient_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

