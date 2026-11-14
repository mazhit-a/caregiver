"""Version 1 API router, mounted under /api by main.py."""

from fastapi import APIRouter

from app.presentation.api.schemas.base import CamelModel
from app.presentation.api.v1.billing import router as billing_router
from app.presentation.api.v1.care_card import router as care_card_router
from app.presentation.api.v1.checkins import router as checkins_router
from app.presentation.api.v1.demo import router as demo_router
from app.presentation.api.v1.lessons import router as lessons_router
from app.presentation.api.v1.phrases import router as phrases_router
from app.presentation.api.v1.plan import router as plan_router
from app.presentation.api.v1.profile import router as profile_router
from app.presentation.api.v1.quiz import router as quiz_router
from app.presentation.api.v1.resources import router as resources_router
from app.presentation.api.v1.roleplay import router as roleplay_router
from app.presentation.api.v1.session import router as session_router
from app.presentation.api.v1.skills import router as skills_router
from app.presentation.api.v1.today import router as today_router
from app.presentation.api.v1.visit_sheet import router as visit_sheet_router
from app.presentation.api.v1.webhooks import router as webhooks_router

router = APIRouter()
router.include_router(resources_router)
router.include_router(quiz_router)
router.include_router(plan_router)
router.include_router(billing_router)
router.include_router(lessons_router)
router.include_router(phrases_router)
router.include_router(checkins_router)
router.include_router(profile_router)
router.include_router(care_card_router)
router.include_router(roleplay_router)
router.include_router(visit_sheet_router)
router.include_router(demo_router)
router.include_router(session_router)
router.include_router(skills_router)
router.include_router(today_router)
router.include_router(webhooks_router)


class HealthResponse(CamelModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
