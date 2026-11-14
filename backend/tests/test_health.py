from fastapi.testclient import TestClient

from app.main import app


def test_health():
    r = TestClient(app).get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_frontend_served():
    r = TestClient(app).get("/")
    assert r.status_code == 200
    assert "CrewCheck" in r.text
