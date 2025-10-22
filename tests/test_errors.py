from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_jwt

client = TestClient(app)


def test_validation_error_users():
    r = client.post("/users", params={"name": ""})
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


def test_not_found_user():
    r = client.get("/users/999")
    assert r.status_code == 404


def test_validation_error_objectives():
    user = client.post("/users", params={"name": "Alice"}).json()

    token = make_jwt(sub=str(user["id"]))
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/objectives", params={"title": ""}, headers=headers)
    assert r.status_code == 422


def test_list_objectives_not_found_user():
    r = client.get("/users/999/objectives")
    assert r.status_code == 404
    body = r.json()
    if r.status_code == 404:
        assert body["code"] == "not_found"


def test_get_objective_not_found():
    r = client.get("/objectives/999")
    assert r.status_code == 404


def test_create_key_result_error_objective_not_found():
    user = client.post("/users", params={"name": "Bob"}).json()
    token = make_jwt(sub=str(user["id"]))
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/key-results",
        params={
            "objective_id": 999,
            "title": "some key result",
            "metric": "%",
            "progress": 0.5,
        },
        headers=headers,
    )

    assert r.status_code == 404, r.text
    body = r.json()
    assert body["code"] == "not_found"
    assert "objective not found" in body["message"]


def test_create_key_result_forbidden_wrong_user():
    user1 = client.post("/users", params={"name": "Alice"}).json()
    user2 = client.post("/users", params={"name": "Bob"}).json()

    token_user1 = make_jwt(sub=str(user1["id"]))
    headers_user1 = {"Authorization": f"Bearer {token_user1}"}

    obj = client.post(
        "/objectives",
        params={
            "user_id": user1["id"],
            "title": "Alice Objective",
            "period": date(2026, 5, 1),
        },
        headers=headers_user1,
    ).json()

    token_user2 = make_jwt(sub=str(user2["id"]))
    headers_user2 = {"Authorization": f"Bearer {token_user2}"}

    r = client.post(
        "/key-results",
        params={
            "objective_id": obj["id"],
            "title": "Bob KR attempt",
            "metric": "%",
            "progress": 0.7,
        },
        headers=headers_user2,
    )

    assert r.status_code == 403, r.text
    body = r.json()
    assert body["detail"] == "Forbidden"
