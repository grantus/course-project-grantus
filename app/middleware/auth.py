import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import Request
from jwt import InvalidTokenError as JWTError
from starlette.responses import JSONResponse

from app.utils.logger import audit_log
from app.utils.secrets import get_jwt_secret

JWT_SECRET = get_jwt_secret()
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "okrs-api")
JWT_ISSUER = os.getenv("JWT_ISSUER", "auth-service")


def make_jwt(sub: str = "1", minutes: int = 5, valid: bool = True):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "aud": JWT_AUDIENCE,
        "iss": JWT_ISSUER,
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=minutes)).timestamp(),
    }

    if not valid:
        payload["nbf"] = (now + timedelta(minutes=10)).timestamp()

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


PUBLIC_PATHS = {
    "/",
    "/health",
    "/robots.txt",
    "/sitemap.xml",
    "/openapi.json",
    "/docs",
    "/redoc",
}


def auth_problem(status_code: int, title: str, detail: str):
    return JSONResponse(
        {
            "type": "https://example.com/problems/auth-error",
            "title": title,
            "status": status_code,
            "detail": detail,
            "correlation_id": str(uuid4()),
        },
        status_code=status_code,
    )


async def auth_middleware(request: Request, call_next):
    raw_path = request.url.path
    path = raw_path.rstrip("/") or "/"
    method = request.method.upper()

    if path in PUBLIC_PATHS:
        response = await call_next(request)
        audit_log(request, "public", "access", "allow")
        return response

    if path.startswith("/users"):
        response = await call_next(request)
        audit_log(request, "public", "access", "allow")
        return response

    if path.startswith("/users/") and path.endswith("/objectives") and method == "GET":
        response = await call_next(request)
        audit_log(request, "public", "access", "allow")
        return response

    if (
        path.startswith("/objectives/") or path.startswith("/key-results/")
    ) and method == "GET":
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        audit_log(request, "anonymous", "auth_missing_header", "deny")
        return auth_problem(
            401,
            "Missing or invalid Authorization header",
            "Missing or invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )

        now = datetime.now(timezone.utc).timestamp()
        exp = payload.get("exp")
        nbf = payload.get("nbf")
        sub = payload.get("sub")

        if not sub:
            return auth_problem(
                401, "Token missing sub claim", "Token missing sub claim"
            )
        if exp and now > exp:
            return auth_problem(401, "Token expired", "Token expired")
        if nbf and now < nbf:
            return auth_problem(401, "Token not yet valid", "Token not yet valid")

        request.state.user = {"id": sub, "claims": payload}

    except JWTError:
        audit_log(request, "anonymous", "auth_invalid_token", "deny")
        return auth_problem(401, "Invalid token", "Invalid token")

    request.state.user = {"id": sub, "claims": payload}
    return await call_next(request)
