"""Access log and last-resort error handling.

The access log writes method, path (card ids redacted, no query string), status and duration:
never a request body, header or query string. Each request gets an id (response header
`X-Request-ID`). An unhandled exception is logged as its type and the request id only (no
message, no traceback: either may hold request values) and answered with the shared 500 shape.
"""

import logging
import uuid
from collections.abc import Callable
from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.presentation.api.error_handlers import error_response

logger = logging.getLogger("app.request")
error_logger = logging.getLogger("app.error")


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp, redact_path: Callable[[str], str]) -> None:
        """`redact_path` hides bearer secrets in the path (wired in `main`, see infrastructure)."""
        self._app = app
        self._redact_path = redact_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        started = perf_counter()
        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        status = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        except Exception as exc:  # last resort: never leak a traceback or a request value
            error_logger.error("unhandled %s request_id=%s", type(exc).__name__, request_id)
            if not response_started:
                response = error_response(
                    500,
                    "internal_error",
                    "Something went wrong on our side. Please try again.",
                    {"requestId": request_id},
                )
                await response(scope, receive, send_wrapper)
        finally:
            logger.info(
                "%s %s -> %s (%.0f ms) request_id=%s",
                scope["method"],
                self._redact_path(scope["path"]),
                status,
                (perf_counter() - started) * 1000,
                request_id,
            )
