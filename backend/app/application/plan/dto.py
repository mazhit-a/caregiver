"""DTOs of the plan use cases."""

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.plan.entities import BuiltPlan
from app.domain.schedule.entities import LessonStatus


@dataclass(frozen=True)
class CompleteResult:
    completed_at: datetime
    rules_version: int
    content_version: str


@dataclass(frozen=True)
class PlanPreviewView:
    plan: BuiltPlan
    rules_version: int
    content_version: str
    built_at: datetime


@dataclass(frozen=True)
class GiftPhrase:
    id: str
    text: str
    when: str


@dataclass(frozen=True)
class GiftSheet:
    title: str
    intro: str
    phrases: list[GiftPhrase]
    footer: str


@dataclass(frozen=True)
class PlanLessonView:
    id: str
    title: str
    minutes: int
    status: LessonStatus
    unlock_on: date | None


@dataclass(frozen=True)
class PlanModuleView:
    id: str
    title: str
    reason: str
    lessons: list[PlanLessonView]


@dataclass(frozen=True)
class PlanView:
    modules: list[PlanModuleView]
    hero_lesson_id: str | None
    lessons_per_week: int
