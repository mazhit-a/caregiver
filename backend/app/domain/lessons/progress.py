"""Per-session progress through one lesson."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.lessons.errors import InvalidLessonStep


@dataclass
class LessonProgress:
    """`step` is the 0-based index of the screen the learner is on; `variant` comes from the
    setup question and only selects wording and examples, never the path."""

    session_id: UUID
    lesson_id: str
    started_at: datetime
    variant: str | None = None
    step: int = 0
    screen_answers: dict[str, Any] = field(default_factory=dict)
    done_at: datetime | None = None

    def move_to(self, step: int, screen_count: int) -> None:
        """Remember the screen the learner is on. The index must exist; a finished lesson keeps
        its step (a done lesson never moves back)."""
        if not 0 <= step < screen_count:
            raise InvalidLessonStep(self.lesson_id, step, screen_count)
        if self.done_at is None:
            self.step = step


@dataclass(frozen=True)
class ScenarioAnswer:
    """One pick on a scenario screen. Retries add rows; nothing is overwritten."""

    session_id: UUID
    lesson_id: str
    screen_id: str
    answer_id: str
    verdict: str
    answered_at: datetime
