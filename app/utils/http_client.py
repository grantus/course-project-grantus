from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class HttpClientError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HttpClientTimeout(HttpClientError):
    def __init__(self, message: str = "request timeout") -> None:
        super().__init__(message)


@dataclass(slots=True)
class SafeHttpClientConfig:
    base_url: str | None = None
    timeout: float = 5.0
    retries: int = 2
    max_connections: int = 10
    max_keepalive_connections: int = 5


class SafeHttpClient:
    def __init__(
        self,
        config: SafeHttpClientConfig | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or SafeHttpClientConfig()

        limits = httpx.Limits(
            max_connections=self.config.max_connections,
            max_keepalive_connections=self.config.max_keepalive_connections,
        )
        self._limits = limits

        kwargs: dict[str, Any] = {
            "timeout": self.config.timeout,
            "limits": limits,
            "transport": transport,
        }
        if self.config.base_url:
            kwargs["base_url"] = self.config.base_url

        self._client = httpx.Client(**kwargs)

    def get_json(self, url: str, **kwargs: Any) -> Any:
        resp = self._request("GET", url, **kwargs)
        return resp.json()

    def post_json(self, url: str, json: Any, **kwargs: Any) -> Any:
        resp = self._request("POST", url, json=json, **kwargs)
        return resp.json()

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None

        for attempt in range(self.config.retries + 1):
            try:
                resp = self._client.request(method, url, **kwargs)

                if 500 <= resp.status_code < 600 and attempt < self.config.retries:
                    continue

                if resp.status_code >= 400:
                    raise HttpClientError(
                        f"HTTP {resp.status_code} from upstream",
                        status_code=resp.status_code,
                    )

                return resp

            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt >= self.config.retries:
                    raise HttpClientTimeout() from exc

            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt >= self.config.retries:
                    raise HttpClientError(f"http error: {exc}") from exc

        raise HttpClientError("failed to perform request") from last_exc

    def close(self) -> None:
        self._client.close()


_http_client: SafeHttpClient | None = None


def get_http_client() -> SafeHttpClient:
    global _http_client
    if _http_client is None:
        _http_client = SafeHttpClient()
    return _http_client


def close() -> None:
    global _http_client
    if _http_client is not None:
        _http_client.close()
        _http_client = None
