import re
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import make_jwt

client = TestClient(app)


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def assert_problem(resp, expected_status):
    assert resp.status_code == expected_status, resp.text
    assert resp.headers.get("content-type", "").startswith("application/problem+json")
    body = resp.json()
    for f in ("type", "title", "status", "detail", "correlation_id"):
        assert f in body, f"missing field {f}: {body}"
    assert body["status"] == expected_status
    assert UUID_RE.match(
        body["correlation_id"]
    ), f"bad correlation_id: {body['correlation_id']}"
    assert "Traceback" not in body["detail"]
    return body


def test_validation_error_users():
    r = client.post("/users", params={"name": ""})
    body = assert_problem(r, 422)
    assert ("validation" in body["type"]) or (
        body["type"] in ("about:blank", "https://example.com/problems/validation-error")
    )
    assert body["title"] or body["detail"]


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
    body = assert_problem(r, 404)
    assert ("not-found" in body["type"]) or (body["title"].lower() == "not found")


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

    body = assert_problem(r, 404)
    assert ("objective not found" in body["detail"].lower()) or (
        body["title"].lower() == "not found"
    )


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


def _auth_headers_for_new_user(name: str = "NFR04-User"):
    user = client.post("/users", params={"name": name}).json()
    token = make_jwt(sub=str(user["id"]))
    return {"Authorization": f"Bearer {token}"}, user


def test_create_objective_error_validation_period_past():
    headers, user = _auth_headers_for_new_user()

    past = date.today() - timedelta(days=1)
    r = client.post(
        "/objectives",
        params={"title": "Fail by period", "period": past},
        headers=headers,
    )

    body = assert_problem(r, 422)
    assert "validation" in body["type"] or body["type"].endswith("/validation-error")
    assert "period" in (body.get("detail") or "").lower() or "title" in body


@pytest.mark.xfail(
    reason="KR сейчас не принимает period; включить после реализации ADR-002 для /key-results"
)
def test_create_key_result_error_validation_period_past():
    headers, user = _auth_headers_for_new_user("NFR04-KR-User")

    future_day = date.today() + timedelta(days=30)
    obj = client.post(
        "/objectives",
        params={"title": "OKR container", "period": future_day},
        headers=headers,
    ).json()

    past = date.today() - timedelta(days=1)
    r = client.post(
        "/key-results",
        params={
            "objective_id": obj["id"],
            "title": "KR with bad period",
            "metric": "%",
            "progress": 0.0,
            "period": past,
        },
        headers=headers,
    )
    body = assert_problem(r, 422)
    assert "validation" in body["type"] or body["type"].endswith("/validation-error")
