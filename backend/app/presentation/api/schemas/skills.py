"""Skills response: scores, counts and the next lesson only (no role-play text fields)."""

from datetime import date
from typing import Literal

from app.presentation.api.schemas.base import CamelModel


class RoleplayProgressOut(CamelModel):
    runs: int
    first_score: int | None
    latest_score: int | None
    max_score: int


class ScenarioProgressOut(CamelModel):
    practised: int
    best: int


class SkillOut(CamelModel):
    id: str
    label: str
    roleplay: RoleplayProgressOut | None
    scenarios: ScenarioProgressOut | None


class ConfidenceOut(CamelModel):
    day0: int | None
    first: dict[str, int] | None
    latest: dict[str, int] | None


class CountsOut(CamelModel):
    scenarios_practised: int
    phrases_saved: int
    tasks_tried: int
    tasks_helped: int


class NextLessonOut(CamelModel):
    lesson_id: str
    title: str
    module_id: str
    reason: str
    status: Literal["locked", "available", "in_progress", "done", "coming_later"]
    unlock_on: date | None


class SkillsResponse(CamelModel):
    skills: list[SkillOut]
    confidence: ConfidenceOut
    counts: CountsOut
    next: NextLessonOut | None
