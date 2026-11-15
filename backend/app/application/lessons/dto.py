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
class RecapView:
    """The opening recap of a lesson: the previous lesson's recap text with the user's phrase."""

    from_lesson_id: str
    text: str


@dataclass(frozen=True)
class LessonView:
    lesson: RenderedLesson
    unlock_on: date
    progress: ProgressView
    recap: RecapView | None = None
    screen_count: int = 0  # all screens of the lesson, whether or not the learner sees them yet


@dataclass(frozen=True)
class AnswerView:
    screen_id: str
    screen_type: str
    result: dict[str, Any]


@dataclass(frozen=True)
class NextLessonView:
    lesson_id: str
    title: str
    module_id: str
    reason: str
    unlock_on: date


@dataclass(frozen=True)
class CompleteView:
    """`wrap` is the lesson's rendered wrap screen (None when it has none). `next_lesson` is None
    when no later lesson is built; `all_done_line` is then the lesson's own closing text."""

    lesson_id: str
    done_at: datetime
    wrap: dict[str, Any] | None
    next_lesson: NextLessonView | None
    all_done_line: str | None
