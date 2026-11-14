"""Per-session progress through one lesson."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


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
