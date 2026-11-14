"""Composition root: the only module that knows every layer."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.clock import SystemClock
from app.infrastructure.config import Settings
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.db.session import create_engine, create_session_factory
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.tokens import SecretsTokenGenerator, UuidGenerator
from app.presentation.api.deps import AppInfo
from app.presentation.api.error_handlers import register_error_handlers
from app.presentation.api.v1.router import router as v1_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Invalid or missing content raises ContentLoadError here, so the app refuses to start.
        app.state.content = JsonContentProvider.from_directory(settings.content_dir)
        yield
        await app.state.engine.dispose()

    app = FastAPI(
        lifespan=lifespan,
        title="Parent Care Navigator",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.app_info = AppInfo(demo_controls=settings.demo_controls)
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)
    app.state.clock = SystemClock()
    app.state.token_generator = SecretsTokenGenerator()
    app.state.id_generator = UuidGenerator()
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_error_handlers(app)
    app.include_router(v1_router, prefix="/api")
    return app


app = create_app
