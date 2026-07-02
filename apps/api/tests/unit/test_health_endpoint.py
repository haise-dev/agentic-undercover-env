from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_endpoint_status_code():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_body_content():
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "aue-api"
    assert data["version"] == "1.0.0"


def test_health_endpoint_has_environment():
    response = client.get("/health")
    data = response.json()
    assert "environment" in data
    assert data["environment"] == "test"
