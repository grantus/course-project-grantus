from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_jwt

client = TestClient(app)


def test_create_and_get_user_success():
    token = make_jwt(sub="1")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/users", params={"name": "Alice"}, headers=headers)
    assert r.status_code == 200
    user = r.json()

    r = client.get(f"/users/{user['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == user["id"]
    assert body["name"] == user["name"]


def test_create_and_get_objective_success():
    user = client.post("/users", params={"name": "Alice"}).json()
    token = make_jwt(sub=str(user["id"]))
    headers = {"Authorization": f"Bearer {token}"}

    obj = client.post(
        "/objectives",
        params={
            "title": "some objective",
            "period": date(2026, 3, 3),
        },
        headers=headers,
    ).json()

    r = client.get(f"/objectives/{obj['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == obj["id"]
    assert body["title"] == obj["title"]


def test_create_key_result_success():
    user = client.post("/users", params={"name": "Alice"}).json()
    token = make_jwt(sub=str(user["id"]))
    headers = {"Authorization": f"Bearer {token}"}

    obj = client.post(
        "/objectives",
        params={
            "user_id": user["id"],
            "title": "some objective",
            "period": date(2026, 6, 6),
        },
        headers=headers,
    ).json()

    r = client.post(
        "/key-results",
        params={
            "objective_id": obj["id"],
            "title": "some key result",
            "metric": "%",
            "progress": 0.1,
        },
        headers=headers,
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "some key result"
    assert body["objective_id"] == obj["id"]
