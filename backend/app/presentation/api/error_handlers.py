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
    "quiz_incomplete": 422,
    "payment_required": 402,  # NoPlan and AccessDenied (the access gate), with details.reason
    "consent_required": 422,
    "unknown_plan": 422,
    "already_subscribed": 409,
    "invalid_transition": 409,
    "unknown_lesson": 404,
    "lesson_not_available": 404,
    "lesson_locked": 423,
    "unknown_screen": 422,
    "invalid_screen_answer": 422,
    "no_subscription_period": 409,
    "no_active_subscription": 409,
    "not_a_stripe_subscription": 409,
    "payment_gateway_error": 502,
    "billing_cancel_failed": 503,
    "checkout_not_found": 404,
    "invalid_webhook_signature": 400,
    "invalid_phrase": 422,
    "phrase_limit_reached": 422,
    "phrase_not_found": 404,
    "checkin_plan_not_found": 404,
    "checkin_already_answered": 409,
    "checkin_not_due": 409,
    "invalid_checkin_answer": 422,
    "invalid_reply": 422,
    "invalid_profile": 422,
    "rate_limited": 429,
    "run_not_found": 404,
    "run_finished": 409,
    "round_mismatch": 422,
    "too_many_previous_turns": 422,
    "turns_mismatch": 422,
    "invalid_visit_sheet": 422,
    "unknown_visit_question": 422,
    "card_not_found": 404,
    "card_revoked": 410,
    "card_already_published": 409,
    "card_not_published": 409,
    "invalid_card_phrases": 422,
    "unknown_event": 422,
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
