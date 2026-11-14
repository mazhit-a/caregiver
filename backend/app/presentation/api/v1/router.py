"""Version 1 API router, mounted under /api by main.py."""

from fastapi import APIRouter

from app.presentation.api.schemas.base import CamelModel

router = APIRouter()


class HealthResponse(CamelModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
