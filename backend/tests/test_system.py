from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_ready() -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["data"]["database"] == "connected"


def test_version() -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    assert response.json()["data"]["version"] == "0.1.0"


def test_openapi() -> None:
    assert client.get("/openapi.json").status_code == 200
