import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request, status
from jwt import InvalidTokenError as JWTError

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


PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/users"}


async def auth_middleware(request: Request, call_next):
    path = request.url.path.rstrip("/")
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
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
            raise HTTPException(status_code=401, detail="Token missing sub claim")
        if exp and now > exp:
            raise HTTPException(status_code=401, detail="Token expired")
        if nbf and now < nbf:
            raise HTTPException(status_code=401, detail="Token not yet valid")

        request.state.user = {"id": sub, "claims": payload}

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    request.state.user = {"id": sub, "claims": payload}
    return await call_next(request)
