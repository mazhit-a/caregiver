"""The saved quiz of one session."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.quiz.answers import normalize_answer
from app.domain.quiz.definition import QuizDefinition
from app.domain.quiz.errors import QuizIncomplete, QuizLocked
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
    health_answers_purged_at: datetime | None = None

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

    def missing_required(self, definition: QuizDefinition) -> list[str]:
        """Ids of the non-skippable questions without an answer, in quiz order."""
        return [q for q in definition.required_question_ids() if self.answers.get(q) is None]

    def complete(self, definition: QuizDefinition, at: datetime) -> None:
        """Mark the quiz completed; requires every non-skippable question and an unlocked quiz."""
        if self.locked:
            raise QuizLocked("The quiz can no longer be changed.")
        missing = self.missing_required(definition)
        if missing:
            raise QuizIncomplete("Some questions still need an answer.", {"questionIds": missing})
        self.completed_at = at

    def purge_health_answers(self, definition: QuizDefinition, at: datetime) -> bool:
        """Delete the raw Q3/Q5 answers; tags, branch and the plan stay. Runs once.

        Returns True when it purged now, False when it had already run.
        """
        if self.health_answers_purged_at is not None:
            return False
        for question_id in definition.health_question_ids():
            self.answers.pop(question_id, None)
        self.health_answers_purged_at = at
        return True

    def lock(self) -> None:
        """No answer or completion changes after the subscription started."""
        self.locked = True
