"""Composition root: the only module that knows every layer."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application.roleplay.limiter import LlmConcurrencyLimiter
from app.infrastructure.clock import SystemClock
from app.infrastructure.config import Settings
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.db.session import create_engine, create_session_factory
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.llm.factory import build_coach
from app.infrastructure.logging import configure_logging, redact_path
from app.infrastructure.payments.pricing_check import ensure_stripe_ids_resolved
from app.infrastructure.payments.stripe_gateway import StripePaymentGateway
from app.infrastructure.payments.webhook_parser import StripeWebhookParser
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.tokens import SecretsTokenGenerator, UuidGenerator
from app.presentation.api.deps import AppInfo
from app.presentation.api.error_handlers import register_error_handlers
from app.presentation.api.http_guards import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.presentation.api.request_logging import RequestLogMiddleware
from app.presentation.api.v1.router import router as v1_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Invalid or missing content raises ContentLoadError here, so the app refuses to start.
        app.state.content = JsonContentProvider.from_directory(settings.content_dir)
        if settings.stripe_enabled:
            # Refuse to start with placeholder price/coupon ids: checkout would fail at runtime.
            ensure_stripe_ids_resolved(app.state.content.pricing())
        yield
        await app.state.engine.dispose()

    app = FastAPI(
        lifespan=lifespan,
        title="Parent Care Navigator",
        docs_url="/api/docs" if settings.docs_enabled else None,
        openapi_url="/api/openapi.json" if settings.docs_enabled else None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.app_info = AppInfo(demo_controls=settings.demo_controls)
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)
    app.state.clock = SystemClock()
    # None without a real Stripe test key: checkout then answers 502 with the demo-mode hint.
    app.state.payment_gateway = (
        StripePaymentGateway.from_api_key(settings.stripe_secret_key)
        if settings.stripe_enabled
        else None
    )
    app.state.webhook_parser = StripeWebhookParser(settings.stripe_webhook_secret)
    app.state.token_generator = SecretsTokenGenerator()
    app.state.coach = build_coach(settings)
    app.state.rate_limiter = InMemoryRateLimiter(settings.roleplay_turns_per_hour)
    app.state.card_rate_limiter = InMemoryRateLimiter(
        settings.public_card_requests_per_minute, timedelta(minutes=1)
    )
    # In-memory limiters hold their counters in this process: run ONE uvicorn worker (the
    # Dockerfile does). A second worker would multiply every limit; swap the `RateLimiter`
    # port implementation (e.g. Redis) before scaling out.
    app.state.session_rate_limiter = InMemoryRateLimiter(
        settings.session_creations_per_minute, timedelta(minutes=1)
    )
    app.state.events_rate_limiter = InMemoryRateLimiter(
        settings.events_requests_per_minute, timedelta(minutes=1)
    )
    app.state.llm_limiter = LlmConcurrencyLimiter(4)  # one per process
    app.state.id_generator = UuidGenerator()
    # Outermost last: request log (ids, 500 shape) > CORS > security headers > body size limit.
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.cors_origin_list:
        # Explicit origins only. No cookies are used (the session token is a header), so
        # credentials stay off; a wildcard origin is refused by Settings.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Content-Type", "X-Session-Token"],
            allow_credentials=False,
            max_age=600,
        )
    app.add_middleware(RequestLogMiddleware, redact_path=redact_path)
    register_error_handlers(app)
    app.include_router(v1_router, prefix="/api")
    return app


app = create_app
