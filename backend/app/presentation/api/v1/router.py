"""Version 1 API router, mounted under /api by main.py."""

from fastapi import APIRouter

from app.presentation.api.schemas.base import CamelModel
from app.presentation.api.v1.plan import router as plan_router
from app.presentation.api.v1.quiz import router as quiz_router
from app.presentation.api.v1.resources import router as resources_router
from app.presentation.api.v1.session import router as session_router

router = APIRouter()
router.include_router(resources_router)
router.include_router(quiz_router)
router.include_router(plan_router)
router.include_router(session_router)


class HealthResponse(CamelModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
