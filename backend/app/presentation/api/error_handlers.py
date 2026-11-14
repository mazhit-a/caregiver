"""Maps errors to the shared shape {"error": {"code", "message", "details"}} in one place."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.shared.errors import DomainError
from app.presentation.api.schemas.base import ErrorBody, ErrorResponse

# The single status-code table: HTTP status -> default error code.
STATUS_CODE_TABLE: dict[int, str] = {
    401: "unauthorized",
    402: "payment_required",
    404: "not_found",
    409: "conflict",
    410: "gone",
    413: "payload_too_large",
    422: "validation_error",
    423: "locked",
    429: "rate_limited",
    502: "bad_gateway",
    503: "service_unavailable",
}

# Domain error code -> HTTP status. Later increments add rows here only.
DOMAIN_ERROR_STATUS: dict[str, int] = {
    "invalid_session_token": 401,
    "invalid_timezone": 422,
    "quiz_locked": 409,
    "invalid_answer": 422,
    "unknown_question": 404,
}


def error_response(
    status_code: int, code: str, message: str, details: dict[str, object] | None = None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or {}))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def _http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = STATUS_CODE_TABLE.get(exc.status_code, "http_error")
    return error_response(exc.status_code, code, str(exc.detail))


async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Never echo the request body (it may hold quiz or profile data): locations and types only.
    errors: list[object] = [
        {"loc": list(e["loc"]), "type": e["type"], "message": e["msg"]} for e in exc.errors()
    ]
    return error_response(422, "validation_error", "The request is not valid.", {"errors": errors})


async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
    status = DOMAIN_ERROR_STATUS.get(exc.code, 500)
    return error_response(status, exc.code, exc.message, exc.details)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(DomainError, _domain_error)  # type: ignore[arg-type]
