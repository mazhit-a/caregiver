"""The saved quiz of one session."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.quiz.answers import normalize_answer
from app.domain.quiz.definition import QuizDefinition
from app.domain.quiz.errors import QuizLocked
from app.domain.quiz.tags import derive


@dataclass
class QuizState:
    session_id: UUID
    answers: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    branch: str | None = None
    last_question_id: str | None = None
    completed_at: datetime | None = None
    locked: bool = False

    def answer(self, definition: QuizDefinition, question_id: str, value: Any) -> None:
        """Validate and save one answer, then recompute tags, branch and the resume point."""
        if self.locked:
            raise QuizLocked("The quiz can no longer be changed.")
        spec = definition.answerable_question(question_id)
        self.answers[spec.id] = normalize_answer(spec, value)
        derived = derive(definition, self.answers)
        self.tags = list(derived.tags)
        self.branch = derived.branch
        self.last_question_id = self._furthest_answered(definition)

    def _furthest_answered(self, definition: QuizDefinition) -> str | None:
        answered = [q.id for q in definition.questions if q.id in self.answers]
        return answered[-1] if answered else None
