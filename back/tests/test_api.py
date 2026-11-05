from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_generate_rejects_invalid_preferences():
    response = client.post(
        "/api/generate",
        json={"goal": "nope", "level": "beginner", "days_per_week": 3,
              "session_duration_minutes": 45, "equipment": ["full_gym"]},
    )
    assert response.status_code == 422
