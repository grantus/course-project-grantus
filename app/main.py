from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.middleware.auth import auth_middleware
from app.utils.logger import audit_log

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="SecDev Course App", version="0.1.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)  # type: ignore[arg-type]
app.middleware("http")(auth_middleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):  # noqa: ARG001
    audit_log(request, "system", "rate_limit_exceeded", "deny")
    return JSONResponse(status_code=429, content={"error": "Too many requests"})


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    audit_log(request, "system", f"api_error_{exc.code}", "error")
    return JSONResponse(
        status_code=exc.status,
        content={"code": exc.code, "message": exc.message},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    audit_log(request, "system", f"http_exception_{exc.status_code}", "error")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": exc.detail,
            "status": exc.status_code,
            "correlation_id": "req-" + str(id(request)),
        },
    )


@app.get("/health")
def health(request: Request):
    audit_log(request, "system", "health_check", "allow")
    return {"status": "ok"}


_DB = {
    "users": [],
    "objectives": [],
    "key_results": [],
}


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
    new_user = {"id": len(_DB["users"]) + 1, "name": name}
    _DB["users"].append(new_user)
    audit_log(request, "system", "create_user", "allow")
    return new_user


@app.get("/users/{user_id}")
def get_user(request: Request, user_id: int):
    for it in _DB["users"]:
        if it["id"] == user_id:
            audit_log(request, "system", f"get_user_{user_id}", "allow")
            return it
    audit_log(request, "system", f"get_user_{user_id}", "not_found")
    raise ApiError(code="not_found", message="item not found", status=404)


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

    if period < date.today().replace(day=1):
        audit_log(request, str(user_id), "create_objective_invalid_period", "error")
        raise ApiError(
            code="validation_error",
            message="period must be today's date or later",
            status=422,
        )

    obj = {
        "id": len(_DB["objectives"]) + 1,
        "user_id": user_id,
        "title": title,
        "period": period,
    }
    _DB["objectives"].append(obj)
    audit_log(request, str(user_id), f"create_objective_{obj['id']}", "allow")
    return obj


@app.get("/users/{user_id}/objectives")
def get_user_objectives(request: Request, user_id: int):
    if not any(user["id"] == user_id for user in _DB["users"]):
        audit_log(request, "system", f"get_user_objectives_{user_id}", "not_found")
        raise ApiError(code="not_found", message="user not found", status=404)
    objectives = [obj for obj in _DB["objectives"] if obj["user_id"] == user_id]
    audit_log(request, "system", f"get_user_objectives_{user_id}", "allow")
    return objectives


@app.get("/objectives/{obj_id}")
def get_objective(request: Request, obj_id: int):
    for obj in _DB["objectives"]:
        if obj["id"] == obj_id:
            audit_log(request, "system", f"get_objective_{obj_id}", "allow")
            return obj
    audit_log(request, "system", f"get_objective_{obj_id}", "not_found")
    raise ApiError(code="not_found", message="objective not found", status=404)


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

    obj = next((o for o in _DB["objectives"] if o["id"] == objective_id), None)
    if not obj:
        audit_log(
            request, user["id"], f"create_key_result_obj_{objective_id}", "not_found"
        )
        raise ApiError(code="not_found", message="objective not found", status=404)

    if int(obj["user_id"]) != int(user["id"]):
        audit_log(request, user["id"], "create_key_result_forbidden", "deny")
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    kr = {
        "id": len(_DB["key_results"]) + 1,
        "objective_id": objective_id,
        "title": title,
        "metric": metric,
        "progress": progress,
    }
    _DB["key_results"].append(kr)

    audit_log(request, user["id"], f"create_key_result_{kr['id']}", "allow")
    return kr
