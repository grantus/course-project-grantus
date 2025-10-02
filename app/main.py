from datetime import date

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="SecDev Course App", version="0.1.0")


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Normalize FastAPI HTTPException into our error envelope
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": detail}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# Example minimal entity (for tests/demo)
_DB = {
    "users": [],
    "objectives": [],
    "key_results": [],
}


@app.post("/users")
def create_user(name: str):
    if not name or len(name) > 100:
        raise ApiError(
            code="validation_error", message="name must be 1..100 chars", status=422
        )
    user = {"id": len(_DB["users"]) + 1, "name": name}
    _DB["users"].append(user)
    return user


@app.get("/users/{user_id}")
def get_user(user_id: int):
    for it in _DB["users"]:
        if it["id"] == user_id:
            return it
    raise ApiError(code="not_found", message="item not found", status=404)


@app.post("/objectives")
def create_objective(user_id: int, title: str, period: date):
    if not any(user["id"] == user_id for user in _DB["users"]):
        raise ApiError(code="not_found", message="user not found", status=404)

    if not title or len(title) > 100:
        raise ApiError(
            code="validation_error", message="title must be 1..100 chars", status=422
        )

    if period < date.today().replace(day=1):
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
    return obj


@app.get("/objectives/{obj_id}")
def get_objective(obj_id: int):
    for o in _DB["objectives"]:
        if o["id"] == obj_id:
            return o
    raise ApiError(code="not_found", message="objective not found", status=404)


@app.get("/users/{user_id}/objectives")
def get_user_objectives(user_id: int):
    if not any(user["id"] == user_id for user in _DB["users"]):
        raise ApiError(code="not_found", message="user not found", status=404)
    objectives = [obj for obj in _DB["objectives"] if obj["user_id"] == user_id]
    return objectives


@app.post("/key-results")
def create_key_result(
    objective_id: int, title: str, metric: str, progress: float = 0.0
):
    if not title or len(title) > 200:
        raise ApiError(
            code="validation_error", message="title must be 1..100 chars", status=422
        )
    if progress < 0 or progress > 1:
        raise ApiError(
            code="validation_error", message="progress must be 0..1", status=422
        )

    if not any(obj["id"] == objective_id for obj in _DB["objectives"]):
        raise ApiError(code="not_found", message="objective not found", status=404)

    kr = {
        "id": len(_DB["key_results"]) + 1,
        "objective_id": objective_id,
        "title": title,
        "metric": metric,
        "progress": progress,
    }
    _DB["key_results"].append(kr)
    return kr
