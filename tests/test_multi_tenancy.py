"""Tests for Multi-Tenant isolation, Indian patient management, screening, and analytics."""

import io
import json
import pytest
from PIL import Image
import numpy as np


def test_list_hospitals(client):
    """Verifies public hospital directory returns active screening facilities."""
    response = client.get("/api/auth/hospitals")
    assert response.status_code == 200
    data = response.get_json()
    assert "hospitals" in data
    assert data["count"] >= 3
    ids = [h["id"] for h in data["hospitals"]]
    assert "apex-retina-lucknow" in ids
    assert "shroff-eye-delhi" in ids
    assert "sankara-eye-bengaluru" in ids


def test_user_authentication_success_and_failure(client):
    """Verifies role-based login and wrong credentials handling."""
    # 1. Valid hospital admin login
    res = client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "apex-retina-lucknow"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["role"] == "hospital_admin"
    assert data["hospital"]["city"] == "Lucknow"

    # 2. Invalid password
    res_bad = client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "wrongpassword",
        "tenant_id": "apex-retina-lucknow"
    })
    assert res_bad.status_code == 401

    # 3. Wrong tenant ID
    res_wrong_tenant = client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "shroff-eye-delhi"
    })
    assert res_wrong_tenant.status_code == 401

    # 4. Invalid non-object and non-string payloads
    res_non_json = client.post("/api/auth/login", data="plain text", content_type="text/plain")
    assert res_non_json.status_code == 400

    res_bad_types = client.post("/api/auth/login", json={"username": 12345, "password": True})
    assert res_bad_types.status_code == 400


def test_strict_tenant_patient_isolation(client):
    """
    CRITICAL SECURITY & AUTHORIZATION CHECK:
    1. Unauthenticated requests return 401.
    2. Cross-tenant header mismatches return 403.
    3. Delhi attempts to read Lucknow patient return 403 or 404.
    4. Unauthenticated staff additions return 401.
    """
    # 1. Unauthenticated patient read rejected with 401
    client.post("/api/auth/logout")
    res_unauth = client.get("/api/patients", headers={"X-Tenant-ID": "apex-retina-lucknow"})
    assert res_unauth.status_code == 401

    # 2. Unauthenticated POST to /api/tenants/<id>/users rejected with 401
    res_unauth_user = client.post("/api/tenants/apex-retina-lucknow/users", json={
        "username": "new_doc", "password": "docpassword1",
        "full_name": "Dr. Test", "role": "ophthalmologist", "email": "test@apex.org"
    })
    assert res_unauth_user.status_code == 401

    # 3. Log in as Lucknow Doctor
    res_login_lko = client.post("/api/auth/login", json={
        "username": "dr_saxena",
        "password": "doctor123",
        "tenant_id": "apex-retina-lucknow"
    })
    assert res_login_lko.status_code == 200

    # 4. Lucknow session using Delhi X-Tenant-ID is rejected with 403
    res_cross_hdr = client.get("/api/patients", headers={"X-Tenant-ID": "shroff-eye-delhi"})
    assert res_cross_hdr.status_code == 403

    # 5. Fetch patients for Lucknow
    res_lko = client.get("/api/patients", headers={"X-Tenant-ID": "apex-retina-lucknow"})
    assert res_lko.status_code == 200
    lko_data = res_lko.get_json()
    lko_patients = lko_data["patients"]
    assert len(lko_patients) >= 20
    for p in lko_patients:
        assert p["tenant_id"] == "apex-retina-lucknow"

    # 6. Log in as Delhi Doctor
    res_login_dlh = client.post("/api/auth/login", json={
        "username": "dr_batra",
        "password": "doctor123",
        "tenant_id": "shroff-eye-delhi"
    })
    assert res_login_dlh.status_code == 200

    # 7. Fetch patients for Delhi
    res_dlh = client.get("/api/patients", headers={"X-Tenant-ID": "shroff-eye-delhi"})
    assert res_dlh.status_code == 200
    dlh_data = res_dlh.get_json()
    dlh_patients = dlh_data["patients"]
    assert len(dlh_patients) >= 10
    for p in dlh_patients:
        assert p["tenant_id"] == "shroff-eye-delhi"

    # Ensure zero overlap
    lko_ids = {p["id"] for p in lko_patients}
    dlh_ids = {p["id"] for p in dlh_patients}
    assert lko_ids.isdisjoint(dlh_ids), "Cross-tenant patient leak detected!"

    # 8. Cross-tenant access attempt: Delhi attempts to read Lucknow patient
    first_lko_id = lko_patients[0]["id"]
    res_leak_attempt = client.get(
        f"/api/patients/{first_lko_id}",
        headers={"X-Tenant-ID": "shroff-eye-delhi"}
    )
    assert res_leak_attempt.status_code == 404, "Tenant boundary breached!"


def test_register_indian_patient(client):
    """Verifies registering a new Indian screening patient with diabetes parameters."""
    client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "apex-retina-lucknow"
    })

    new_patient_payload = {
        "first_name": "Vikram",
        "last_name": "Singhania",
        "gender": "Male",
        "dob": "1974-05-18",
        "age": 52,
        "phone": "+91 98200 11223",
        "email": "vikram.singhania@mumbai.com",
        "address": "Flat 801, Sea View Towers, Worli",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400018",
        "diabetes_type": "Type 2",
        "diabetes_duration_years": 11.5,
        "hba1c": 8.3,
        "insulin_dependent": 1,
        "hypertension": 1,
        "smoker": 0,
        "clinical_notes": "Referred by diabetologist for annual retinal examination."
    }

    res = client.post(
        "/api/patients",
        headers={"X-Tenant-ID": "apex-retina-lucknow"},
        json=new_patient_payload
    )
    assert res.status_code == 201
    data = res.get_json()["patient"]
    assert data["first_name"] == "Vikram"
    assert data["tenant_id"] == "apex-retina-lucknow"
    assert data["diabetes_type"] == "Type 2"
    assert data["is_minor"] == 0

    # Duplicate registration attempt with same name and DOB should return 409 Conflict
    dup_res = client.post(
        "/api/patients",
        headers={"X-Tenant-ID": "apex-retina-lucknow"},
        json=new_patient_payload
    )
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.get_json()["error"]


def test_register_minor_patient_with_guardian(client):
    """Verifies adolescent screening registration automatically flags minor and retains guardian."""
    client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "apex-retina-lucknow"
    })

    minor_payload = {
        "first_name": "Rohan",
        "last_name": "Deshmukh",
        "gender": "Male",
        "dob": "2011-09-12",
        "age": 15,
        "phone": "+91 98220 99881",
        "address": "45 Shivaji Nagar",
        "city": "Pune",
        "state": "Maharashtra",
        "pincode": "411005",
        "diabetes_type": "Type 1",
        "diabetes_duration_years": 4.0,
        "hba1c": 7.4,
        "guardian_name": "Ashok Deshmukh",
        "guardian_relation": "Father",
        "guardian_phone": "+91 98220 99881",
        "clinical_notes": "Adolescent Type 1 Diabetes screening check."
    }

    res = client.post(
        "/api/patients",
        headers={"X-Tenant-ID": "apex-retina-lucknow"},
        json=minor_payload
    )
    assert res.status_code == 201
    patient = res.get_json()["patient"]
    assert patient["is_minor"] == 1
    assert patient["guardian_name"] == "Ashok Deshmukh"


def test_patient_age_group_filtering_dob_derived(client):
    """Verifies that min_age and max_age filter patients using dob-derived current age."""
    client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "apex-retina-lucknow"
    })

    # Query with min_age=18 and max_age=40 (Young adults)
    res_young = client.get(
        "/api/patients?min_age=18&max_age=40",
        headers={"X-Tenant-ID": "apex-retina-lucknow"}
    )
    assert res_young.status_code == 200
    data_young = res_young.get_json()
    assert data_young["total"] > 0
    for p in data_young["patients"]:
        # Verify age bounds
        assert 18 <= p["age"] <= 40

    # Query with max_age=17 (Pediatric / Minor)
    res_minor = client.get(
        "/api/patients?max_age=17",
        headers={"X-Tenant-ID": "apex-retina-lucknow"}
    )
    assert res_minor.status_code == 200
    data_minor = res_minor.get_json()
    for p in data_minor["patients"]:
        assert p["age"] <= 17


def test_screening_creation_and_ai_inference(client, sample_grade3_bytes):
    """Verifies fundus image upload, live inference, and database persistence."""
    client.post("/api/auth/login", json={
        "username": "dr_saxena",
        "password": "doctor123",
        "tenant_id": "apex-retina-lucknow"
    })

    # 1. Fetch a patient
    res_pat = client.get("/api/patients", headers={"X-Tenant-ID": "apex-retina-lucknow"})
    patient_id = res_pat.get_json()["patients"][0]["id"]

    # 2. Post screening multipart image
    data = {
        "patient_id": patient_id,
        "eye": "Left Eye (OS)",
        "notes": "Patient reports blurred vision."
    }
    data["image"] = (io.BytesIO(sample_grade3_bytes), "patient_retina.png")

    res = client.post(
        "/api/screenings",
        headers={"X-Tenant-ID": "apex-retina-lucknow"},
        data=data,
        content_type="multipart/form-data"
    )
    assert res.status_code == 201
    screening = res.get_json()["screening"]
    assert screening["patient_id"] == patient_id
    assert screening["tenant_id"] == "apex-retina-lucknow"
    assert screening["grade"] in (0, 1, 2, 3, 4)
    assert screening["confidence"] > 0
    assert "heatmap_image_path" in screening
    assert len(screening["probabilities"]) == 5


def test_hospital_analytics_endpoint(client):
    """Verifies calculated screening statistics for a specific hospital."""
    client.post("/api/auth/login", json={
        "username": "dr_saxena",
        "password": "doctor123",
        "tenant_id": "apex-retina-lucknow"
    })

    res = client.get("/api/analytics", headers={"X-Tenant-ID": "apex-retina-lucknow"})
    assert res.status_code == 200
    stats = res.get_json()
    assert stats["tenant_id"] == "apex-retina-lucknow"
    assert stats["total_patients"] >= 20
    assert stats["total_screenings"] >= 20
    assert 0.0 <= stats["positivity_rate"] <= 100.0
    assert len(stats["severity_distribution"]) == 5
    # Sum of percentages should be ~100%
    pct_sum = sum(s["percentage"] for s in stats["severity_distribution"])
    assert 95.0 <= pct_sum <= 105.0
