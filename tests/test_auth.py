from datetime import date

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_user_creation():
    r = client.post("/users", params={"name": "Alice"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Alice"
    assert "id" in body


def test_create_objective_unauthorized():
    try:
        r = client.post(
            "/objectives",
            params={
                "title": "Unauthorized objective",
                "period": date(2026, 1, 1),
            },
        )
    except Exception as e:
        assert "401" in str(e)
        return

    assert r.status_code == 401
    body = r.json()
    assert body["status"] == 401
    assert "Missing or invalid" in body["title"]


def test_create_key_result_unauthorized():
    try:
        r = client.post(
            "/key_result",
            params={
                "title": "Unauthorized objective",
                "period": date(2026, 1, 1),
            },
        )
    except Exception as e:
        assert "401" in str(e)
        return

    assert r.status_code == 401
    body = r.json()
    assert body["status"] == 401
    assert "Missing or invalid" in body["title"]
