"""ASGI guards: request body size limit (413) and security headers on every response."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.presentation.api.error_handlers import error_response

MAX_BODY_BYTES = 64 * 1024  # Caddy enforces the same limit at the edge (`request_body`)


class BodyTooLarge(Exception):
    """Raised inside the receive channel when a streamed body passes the limit."""


class BodySizeLimitMiddleware:
    """413 `payload_too_large` for a body over `max_bytes`; field limits stay 422 in the schemas.

    Checks `Content-Length` first (no body is read), and counts streamed bytes for requests
    without one (chunked), so the limit cannot be bypassed by omitting the header.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self._app = app
        self._max = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = 0
                if declared > self._max:
                    await self._reject(scope, receive, send)
                    return
        received = 0
        exceeded = False
        started = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max:
                    exceeded = True
                    raise BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if exceeded:
                # FastAPI turns a failed body read into its own 400: the 413 replaces it.
                if not started:
                    started = True
                    await self._reject(scope, receive, send)
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self._app(scope, limited_receive, tracking_send)
        except BodyTooLarge:
            if not started:
                await self._reject(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = error_response(
            413,
            "payload_too_large",
            "The request is too large.",
            {"maxBytes": self._max},
        )
        await response(scope, receive, send)


class SecurityHeadersMiddleware:
    """`Cache-Control: no-store` (responses carry personal data) and `X-Content-Type-Options`.

    HSTS, Referrer-Policy and framing headers belong to Caddy (the TLS terminator).
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                if b"cache-control" not in present:
                    headers.append((b"cache-control", b"no-store"))
                headers.append((b"x-content-type-options", b"nosniff"))
                message = {**message, "headers": headers}
            await send(message)

        await self._app(scope, receive, send_wrapper)
