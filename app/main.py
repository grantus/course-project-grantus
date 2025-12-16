from contextlib import asynccontextmanager
from datetime import date
from typing import Any, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.middleware.auth import auth_middleware
from app.middleware.correlation import CorrelationIdMiddleware
from app.utils import http_client
from app.utils.db import (
    create_key_result_db,
    create_objective_db,
    create_user_db,
    get_objective_db,
    get_user_db,
    init_db,
    list_objectives_for_user_db,
)
from app.utils.logger import audit_log


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    http_client.close()


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="SecDev Course App", version="0.1.0", lifespan=lifespan)
app.add_middleware(cast(Any, CorrelationIdMiddleware))
app.state.limiter = limiter  # type: ignore[attr-defined]
app.add_middleware(SlowAPIMiddleware)  # type: ignore[arg-type]
app.middleware("http")(auth_middleware)


def problem(status: int, title: str, detail: str, type_: str = "about:blank"):
    cid = str(uuid4())
    return JSONResponse(
        {
            "type": type_,
            "title": title,
            "status": status,
            "detail": detail,
            "correlation_id": cid,
        },
        status_code=status,
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    cid = str(uuid4())
    audit_log(request, "system", f"rate_limit_exceeded cid={cid}", "deny")
    return problem(
        429,
        "Too Many Requests",
        "Write operations are rate limited.",
        type_="https://example.com/problems/rate-limit",
    )


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    cid = str(uuid4())
    type_map = {
        "validation_error": "https://example.com/problems/validation-error",
        "not_found": "https://example.com/problems/not-found",
        "auth_error": "https://example.com/problems/auth-error",
    }
    title_map = {
        "validation_error": "Validation error",
        "not_found": "Not Found",
        "auth_error": "Authentication/Authorization error",
    }
    audit_log(request, "system", f"api_error_{exc.code} cid={cid}", "error")

    return problem(
        exc.status,
        title_map.get(exc.code, "Error"),
        exc.message,
        type_=type_map.get(exc.code, "about:blank"),
    )


@app.get("/")
def root(request: Request):
    return {"status": "ok"}


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow:\n"


@app.get("/sitemap.xml")
def sitemap():
    return Response(status_code=404)


@app.get("/health")
def health(request: Request):
    audit_log(request, "system", "health_check", "allow")
    return {"status": "ok"}


def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        audit_log(request, "anonymous", "get_current_user", "deny")
        raise HTTPException(status_code=401, detail="Not authenticated")
    audit_log(request, user.get("id", "unknown"), "get_current_user", "allow")
    return user


@app.post("/users")
def create_user(request: Request, name: str):
    if not name or len(name) > 100:
        audit_log(request, "system", "create_user_invalid_name", "error")
        raise ApiError(
            code="validation_error", message="name must be 1..100 chars", status=422
        )
    row = create_user_db(name)
    audit_log(request, "system", f"create_user_db_{row['id']}", "allow")
    return row


@app.get("/users/{user_id}")
def get_user(request: Request, user_id: int):
    row = get_user_db(user_id)
    if not row:
        audit_log(request, "system", f"get_user_{user_id}", "not_found")
        raise ApiError(code="not_found", message="user not found", status=404)
    audit_log(request, "system", f"get_user_{user_id}", "allow")
    return row


@app.post("/objectives")
def create_objective(
    request: Request, title: str, period: date, user=Depends(get_current_user)
):
    user_id = int(user["id"])

    if not title or len(title) > 100:
        audit_log(request, str(user_id), "create_objective_invalid_title", "error")
        raise ApiError(
            code="validation_error", message="title must be 1..100 chars", status=422
        )

    if period < date.today():
        audit_log(request, str(user_id), "create_objective_invalid_period", "error")
        raise ApiError(
            code="validation_error",
            message="period must be today's date or later",
            status=422,
        )

    obj = create_objective_db(user_id, title, period)
    audit_log(request, str(user_id), f"create_objective_{obj['id']}", "allow")
    return obj


@app.get("/users/{user_id}/objectives")
def get_user_objectives(request: Request, user_id: int):
    user_row = get_user_db(user_id)
    if not user_row:
        audit_log(request, "system", f"get_user_objectives_{user_id}", "not_found")
        raise ApiError(code="not_found", message="user not found", status=404)

    objectives = list_objectives_for_user_db(user_id)
    audit_log(request, "system", f"get_user_objectives_{user_id}", "allow")
    return objectives


@app.get("/objectives/{obj_id}")
def get_objective(request: Request, obj_id: int):
    obj = get_objective_db(obj_id)
    if not obj:
        audit_log(request, "system", f"get_objective_{obj_id}", "not_found")
        raise ApiError(code="not_found", message="objective not found", status=404)
    audit_log(request, "system", f"get_objective_{obj_id}", "allow")
    return obj


@app.post("/key-results")
@limiter.limit("100/minute")
def create_key_result(
    request: Request,
    objective_id: int,
    title: str,
    metric: str,
    progress: float = 0.0,
    user=Depends(get_current_user),
):
    if not title or len(title) > 200:
        audit_log(request, user["id"], "create_key_result_invalid_title", "error")
        raise ApiError(
            code="validation_error", message="title must be 1..100 chars", status=422
        )
    if progress < 0 or progress > 1:
        audit_log(request, user["id"], "create_key_result_invalid_progress", "error")
        raise ApiError(
            code="validation_error", message="progress must be 0..1", status=422
        )

    obj = get_objective_db(objective_id)
    if not obj:
        audit_log(
            request, user["id"], f"create_key_result_obj_{objective_id}", "not_found"
        )
        raise ApiError(code="not_found", message="objective not found", status=404)

    if int(obj["user_id"]) != int(user["id"]):
        audit_log(request, user["id"], "create_key_result_forbidden", "deny")
        raise HTTPException(status_code=403, detail="Forbidden")

    kr = create_key_result_db(objective_id, title, metric, progress)
    audit_log(request, user["id"], f"create_key_result_{kr['id']}", "allow")
    return kr
