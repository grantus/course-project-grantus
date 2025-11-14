import httpx
import pytest

from app.utils.http_client import (
    HttpClientError,
    HttpClientTimeout,
    SafeHttpClient,
    SafeHttpClientConfig,
)


def make_client(transport: httpx.BaseTransport):
    cfg = SafeHttpClientConfig(
        base_url="http://upstream.local",
        timeout=0.1,
        retries=2,
        max_connections=10,
        max_keepalive_connections=5,
    )
    return SafeHttpClient(cfg, transport=transport)


def test_get_json_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = make_client(httpx.MockTransport(handler))

    data = client.get_json("/api")
    assert data == {"ok": True}


def test_retries_on_5xx_then_success():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(200, json={"ok": True})

    client = make_client(httpx.MockTransport(handler))
    data = client.get_json("/whatever")

    assert data == {"ok": True}
    assert calls["n"] == 3


def test_retries_on_5xx_then_fail():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"error": "temporary"})

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(HttpClientError) as exc:
        client.get_json("/always-503")

    assert calls["n"] == client.config.retries + 1
    assert "HTTP 503" in str(exc.value)


def test_retries_on_timeout_then_fail():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("boom")

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(HttpClientTimeout) as exc:
        client.get_json("/timeout")
    assert "request timeout" in str(exc.value)


def test_http_error_4xx_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(HttpClientError) as exc:
        client.get_json("/not-found")

    assert exc.value.status_code == 404
    assert "HTTP 404" in str(exc.value)


def test_connection_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("cannot connect", request=request)

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(HttpClientError) as exc:
        client.get_json("/downstream")
    assert "http error" in str(exc.value).lower()


def test_http_client_stores_limits():
    cfg = SafeHttpClientConfig(
        base_url="http://upstream.local",
        timeout=3.0,
        retries=1,
        max_connections=10,
        max_keepalive_connections=5,
    )
    client = SafeHttpClient(cfg)
    assert client._limits.max_connections == 10
    assert client._limits.max_keepalive_connections == 5
    client.close()
