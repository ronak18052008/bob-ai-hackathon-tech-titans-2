from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "MedBrief AI"

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "backend"

def test_ready_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "not_ready")
    assert data["service"] == "backend"

