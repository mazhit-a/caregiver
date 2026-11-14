"""Quiz request and response schemas."""

from typing import Any

from app.presentation.api.schemas.base import CamelModel


class QuizResponse(CamelModel):
    questions: list[dict[str, Any]]
    answers: dict[str, Any]
    branch: str | None
    last_question_id: str | None
    completed: bool
    locked: bool


class AnswerRequest(CamelModel):
    value: Any = None


class AnswerResponse(CamelModel):
    question_id: str
    branch: str | None
    tags: list[str]
    last_question_id: str | None
