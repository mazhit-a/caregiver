"""Plan funnel response schemas (finished text only)."""

from datetime import date, datetime
from typing import Literal

from app.presentation.api.schemas.base import CamelModel


class CompleteResponse(CamelModel):
    completed: bool
    completed_at: datetime
    rules_version: int
    content_version: str


class PlanLessonOut(CamelModel):
    id: str
    title: str
    minutes: int
    built: bool


class PlanModuleOut(CamelModel):
    id: str
    title: str
    reason: str
    status: str
    in_first_30_days: bool
    lessons: list[PlanLessonOut]


class QuickGuideOut(CamelModel):
    id: str
    title: str
    highlight: bool


class PaceOut(CamelModel):
    lessons_per_week: int
    minutes_per_lesson: int
    label: str


class ReadinessOut(CamelModel):
    modules_total: int
    lessons_total: int


class BeforeAfterOut(CamelModel):
    before: str
    after: str


class PlanPreviewResponse(CamelModel):
    plan_intro: str
    what_we_heard: list[str]
    before_after: BeforeAfterOut
    modules: list[PlanModuleOut]
    first_30_days: list[str]
    first_lesson_id: str
    quick_guides: list[QuickGuideOut]
    loader_lines: list[str]
    pace: PaceOut
    readiness: ReadinessOut
    rules_version: int
    content_version: str
    built_at: datetime


class GiftPhraseOut(CamelModel):
    id: str
    text: str
    when: str


class GiftResponse(CamelModel):
    title: str
    intro: str
    phrases: list[GiftPhraseOut]
    footer: str


class PlanLessonStatusOut(CamelModel):
    id: str
    title: str
    minutes: int
    status: Literal["locked", "available", "in_progress", "done", "coming_later"]
    unlock_on: date | None


class PlanModuleStatusOut(CamelModel):
    id: str
    title: str
    reason: str
    lessons: list[PlanLessonStatusOut]


class PlanResponse(CamelModel):
    """`GET /api/plan`. `unlock_on` is set for every scheduled lesson, null for coming_later."""

    modules: list[PlanModuleStatusOut]
    hero_lesson_id: str | None
    lessons_per_week: int
