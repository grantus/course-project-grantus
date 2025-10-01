from datetime import date

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_not_found_user():
    r = client.get("/users/999")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body and body["error"]["code"] == "not_found"


def test_validation_error_users():
    r = client.post("/users", params={"name": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"


def test_validation_error_objectives():
    user = client.post("/users", params={"name": "Alice"}).json()
    r = client.post(
        "/objectives",
        params={"user_id": user["id"], "title": "", "period": date.today()},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"


def test_list_objectives_not_found_user():
    r = client.get("/users/999/objectives")
    assert r.status_code == 404
    body = r.json()
    if r.status_code == 404:
        assert body["error"]["code"] == "not_found"


def test_get_objective_not_found():
    r = client.get("/objectives/999")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"


def test_create_key_result_error_objective_not_found():
    r = client.post(
        "/key-results",
        params={
            "objective_id": 999,
            "title": "some key result",
            "metric": "%",
            "progress": 0.5,
        },
    )
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"
