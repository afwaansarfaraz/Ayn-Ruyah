"""Integration tests for Flask HTTP endpoints."""

import io


def test_health_check_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["model"] == "EfficientNet-B4 (NoisyStudent)"
    assert data["classes"] == 5


def test_root_serves_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"AYN RUYAH" in response.data or b"RetinaLens AI" in response.data


def test_analyze_unauthenticated_returns_401(client):
    client.post("/api/auth/logout")
    response = client.post("/api/analyze", data={})
    assert response.status_code == 401


def test_analyze_without_image_returns_400(client):
    client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "apex-retina-lucknow"
    })
    response = client.post(
        "/api/analyze",
        headers={"X-Tenant-ID": "apex-retina-lucknow"},
        data={}
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_analyze_with_non_retinal_image_returns_400(client, non_retinal_image_bytes):
    client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "apex-retina-lucknow"
    })
    data = {
        "image": (io.BytesIO(non_retinal_image_bytes), "invalid.jpg")
    }
    response = client.post(
        "/api/analyze",
        headers={"X-Tenant-ID": "apex-retina-lucknow"},
        data=data,
        content_type="multipart/form-data"
    )
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data
    assert "fundus" in json_data["error"] or "retinal" in json_data["error"]


def test_analyze_with_valid_retinal_image_returns_200(client, sample_grade3_bytes):
    client.post("/api/auth/login", json={
        "username": "admin_lucknow",
        "password": "admin123",
        "tenant_id": "apex-retina-lucknow"
    })
    data = {
        "image": (io.BytesIO(sample_grade3_bytes), "sample3.jpg")
    }
    response = client.post(
        "/api/analyze",
        headers={"X-Tenant-ID": "apex-retina-lucknow"},
        data=data,
        content_type="multipart/form-data"
    )
    assert response.status_code == 200
    json_data = response.get_json()

    # Verify complete API contract matching frontend
    assert "grade" in json_data
    assert json_data["grade"] in [0, 1, 2, 3, 4]
    assert "result" in json_data
    assert "severity" in json_data
    assert "confidence" in json_data
    assert "color" in json_data
    assert "recommendation" in json_data
    assert "probabilities" in json_data
    assert len(json_data["probabilities"]) == 5
    assert "heatmap" in json_data
    assert json_data["heatmap"].startswith("data:image/png;base64,")
    assert "demo_mode" in json_data


def test_404_browser_serves_branded_html(client):
    response = client.get("/nonexistent-clinical-route", headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "text/html" in response.content_type
    assert b"Clinical Resource Not Found" in response.data
    assert b"AYN" in response.data


def test_404_api_returns_clean_json(client):
    response = client.get("/api/nonexistent-endpoint", headers={"Accept": "application/json"})
    assert response.status_code == 404
    data = response.get_json()
    assert data["status_code"] == 404
    assert "Resource not found" in data["error"]


def test_403_browser_serves_branded_html(client):
    response = client.get("/403", headers={"Accept": "text/html"})
    assert response.status_code == 403
    assert "text/html" in response.content_type
    assert b"Clinical Access Restricted" in response.data


def test_500_browser_serves_branded_html(client):
    response = client.get("/500", headers={"Accept": "text/html"})
    assert response.status_code == 500
    assert "text/html" in response.content_type
    assert b"Clinical Service Interruption" in response.data


