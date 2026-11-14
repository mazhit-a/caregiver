"""DTOs of the quiz use cases."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QuizView:
    questions: list[dict[str, Any]]  # rendered: no unfilled placeholder
    answers: dict[str, Any]
    branch: str | None
    last_question_id: str | None
    completed: bool
    locked: bool


@dataclass(frozen=True)
class AnswerResult:
    question_id: str
    branch: str | None
    tags: list[str]
    last_question_id: str | None
