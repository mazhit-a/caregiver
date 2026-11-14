"""Composition root: the only module that knows every layer."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.config import Settings
from app.presentation.api.deps import AppInfo
from app.presentation.api.error_handlers import register_error_handlers
from app.presentation.api.v1.router import router as v1_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="Parent Care Navigator",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.app_info = AppInfo(demo_controls=settings.demo_controls)
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
