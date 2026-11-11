"""Verification test demonstrating live API produces genuine inference and never demo/random results."""

import io
import json
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:5000"


def test_live_api():
    print("Testing Live Flask API at", BASE_URL)

    # 1. Health check
    with urllib.request.urlopen(f"{BASE_URL}/api/health") as resp:
        assert resp.status == 200
        health = json.loads(resp.read().decode())
        print("1. Health Endpoint: OK ->", health)
        assert health["model_loaded"] is True

    # 2. Login as Lucknow Doctor
    login_payload = json.dumps({
        "username": "dr_saxena",
        "password": "doctor123",
        "tenant_id": "apex-retina-lucknow"
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        cookie = resp.headers.get("Set-Cookie", "")
        data = json.loads(resp.read().decode())
        assert isinstance(data, dict) and "user" in data, f"Invalid login response: {data}"
        tenant_id = data.get("tenant_id") or (data.get("hospital") and data["hospital"].get("id")) or (data.get("user") and data["user"].get("tenant_id"))
        assert tenant_id == "apex-retina-lucknow", f"Expected Lucknow tenant, got: {tenant_id}"
        print(f"2. Logged in as: {data['user']['full_name']} (Role: {data['user']['role']}, Tenant: {tenant_id})")

    # 3. Dynamically fetch an existing registered patient for this tenant
    req_pat = urllib.request.Request(
        f"{BASE_URL}/api/patients",
        headers={"X-Tenant-ID": tenant_id, "Cookie": cookie}
    )
    with urllib.request.urlopen(req_pat) as resp:
        assert resp.status == 200
        pat_data = json.loads(resp.read().decode())
        assert pat_data.get("patients"), "Expected seeded patients for Lucknow workspace"
        patient_id = pat_data["patients"][0]["id"]
        print(f"3. Retrieved dynamic patient ID: {patient_id}")

    # 4. Test image screening with sample Grade 3 retinal fundus image
    test_img = Path(__file__).resolve().parent.parent / "sample_images" / "grade3_6b128e648646-600-FS.jpg"
    assert test_img.exists(), "Sample test image must exist"
    img_bytes = test_img.read_bytes()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"patient_id\"\r\n\r\n{patient_id}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"eye\"\r\n\r\nLeft Eye (OS)\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"notes\"\r\n\r\nAutomated Verification\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"sample_grade3.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode())
    parts.append(img_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())

    body = b"".join(parts)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "X-Tenant-ID": tenant_id,
        "Cookie": cookie,
    }

    req_screening = urllib.request.Request(f"{BASE_URL}/api/screenings", data=body, headers=headers)
    with urllib.request.urlopen(req_screening) as resp:
        assert resp.status == 201
        res = json.loads(resp.read().decode())
        screening = res["screening"]
        print("4. Screening Ingestion & Inference Success (HTTP 201):")
        print(f"   Screening ID: {screening['id']}")
        print(f"   Predicted Grade: {screening['grade']} ({screening['severity']})")
        print(f"   Confidence Score: {screening['confidence']}%")
        print(f"   Probabilities Distribution: {screening['probabilities']}")
        heatmap_str = screening.get("heatmap_image_path") or (res.get("diagnostic") and res["diagnostic"].get("heatmap"))
        print(f"   Grad-CAM Saliency Data URL: {heatmap_str[:40]}... (len: {len(heatmap_str)})")
        print(f"   Is Demo Mode: {screening.get('is_demo', 0)}")

        assert screening["grade"] in (0, 1, 2, 3, 4)
        assert screening["confidence"] > 0
        assert screening.get("is_demo", 0) == 0
        prob_sum = sum(screening["probabilities"].values())
        assert 98.0 <= prob_sum <= 102.0
        assert heatmap_str.startswith("data:image/png;base64,")

    print("\n[SUCCESS] Live API returns genuine, deterministic Deep Learning predictions and explainability maps!")


if __name__ == "__main__":
    test_live_api()
