from datetime import date

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_get_user_success():
    r = client.post("/users", params={"name": "Alice"})
    assert r.status_code == 200
    user = r.json()

    r = client.get(f"/users/{user['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == user["id"]
    assert body["name"] == user["name"]


def test_create_and_get_objective_success():
    user = client.post("/users", params={"name": "Alice"}).json()
    obj = client.post(
        "/objectives",
        params={
            "user_id": user["id"],
            "title": "some objective",
            "period": date(2026, 3, 3),
        },
    ).json()
    r = client.get(f"/objectives/{obj['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == obj["id"]
    assert body["title"] == obj["title"]
    assert body["period"] == obj["period"]


def test_create_key_result_success():
    user = client.post("/users", params={"name": "Alice"}).json()
    obj = client.post(
        "/objectives",
        params={
            "user_id": user["id"],
            "title": "some objective",
            "period": date(2026, 6, 6),
        },
    ).json()

    r = client.post(
        "/key-results",
        params={
            "objective_id": obj["id"],
            "title": "some key result",
            "metric": "%",
            "progress": 0.1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["objective_id"] == obj["id"]
    assert body["title"] == "some key result"
    assert body["progress"] == 0.1
