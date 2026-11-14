"""The quiz as the domain sees it: question specs built from quiz.json (no wording logic here)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from app.domain.quiz.derived import DerivedTagRule
from app.domain.quiz.errors import UnknownQuestion

QuestionKind = Literal["single", "multi", "grid", "scale", "interstitial"]

RECIPIENT_QUESTION_ID = "q1_recipient"
BRANCH_QUESTION_ID = "q3_situation"


@dataclass(frozen=True)
class OptionSpec:
    id: str
    tags: tuple[str, ...] = ()
    branch: str | None = None
    exclusive: bool = False


@dataclass(frozen=True)
class QuestionSpec:
    """One entry of quiz.json. `display` is the client-facing JSON with placeholders unfilled."""

    id: str
    kind: QuestionKind
    display: Mapping[str, Any]
    health_data: bool = False
    skippable: bool = False
    max_choices: int | None = None
    options: tuple[OptionSpec, ...] = ()
    row_ids: tuple[str, ...] = ()
    state_ids: tuple[str, ...] = ()
    scale_min: int | None = None
    scale_max: int | None = None
    derived_rules: tuple[DerivedTagRule, ...] = field(default=())

    @property
    def answerable(self) -> bool:
        return self.kind != "interstitial"

    def option(self, option_id: str) -> OptionSpec | None:
        return next((o for o in self.options if o.id == option_id), None)


@dataclass(frozen=True)
class QuizDefinition:
    questions: tuple[QuestionSpec, ...]

    def answerable_question(self, question_id: str) -> QuestionSpec:
        for question in self.questions:
            if question.id == question_id and question.answerable:
                return question
        raise UnknownQuestion("There is no such quiz question.", {"questionId": question_id})

    def health_question_ids(self) -> tuple[str, ...]:
        """Questions flagged `healthData` (no trackers; raw answers purged on subscription)."""
        return tuple(q.id for q in self.questions if q.health_data)
