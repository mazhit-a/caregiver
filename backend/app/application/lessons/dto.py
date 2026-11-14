"""DTOs of the lesson use cases."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.domain.lessons.screens import RenderedLesson


@dataclass(frozen=True)
class ProgressView:
    step: int
    started_at: datetime
    done_at: datetime | None


@dataclass(frozen=True)
class LessonView:
    lesson: RenderedLesson
    unlock_on: date
    progress: ProgressView


@dataclass(frozen=True)
class AnswerView:
    screen_id: str
    screen_type: str
    result: dict[str, Any]
