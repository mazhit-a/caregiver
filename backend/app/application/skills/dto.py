"""DTOs of the skills use case."""

from dataclasses import dataclass

from app.domain.schedule.next_lesson import NextLesson
from app.domain.skills.progress import RoleplayProgress, ScenarioProgress


@dataclass(frozen=True)
class SkillView:
    id: str
    label: str
    roleplay: RoleplayProgress | None
    scenarios: ScenarioProgress | None


@dataclass(frozen=True)
class ConfidenceView:
    day0: int | None
    first: dict[str, int] | None
    latest: dict[str, int] | None


@dataclass(frozen=True)
class SkillCounts:
    scenarios_practised: int
    phrases_saved: int
    tasks_tried: int
    tasks_helped: int


@dataclass(frozen=True)
class SkillsView:
    skills: list[SkillView]
    confidence: ConfidenceView
    counts: SkillCounts
    next: NextLesson | None
