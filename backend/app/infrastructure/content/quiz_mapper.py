"""quiz.json models -> the quiz domain definition."""

from typing import Any

from app.domain.quiz.definition import OptionSpec, QuestionSpec, QuizDefinition
from app.domain.quiz.derived import parse_derived_rule
from app.infrastructure.content.schemas import (
    DerivedTag,
    GridQuestion,
    InterstitialQuestion,
    MultiQuestion,
    QuizFile,
    QuizOption,
    QuizQuestion,
    SingleQuestion,
)

# Authoring and rule fields that the client never needs.
_HIDDEN_QUESTION_KEYS = {"usedFor", "derivedTags", "storeAs"}
_HIDDEN_OPTION_KEYS = {"tags", "heard", "branch"}


def to_quiz_definition(quiz: QuizFile) -> QuizDefinition:
    return QuizDefinition(tuple(_question(q) for q in quiz.questions))


def _display(question: QuizQuestion) -> dict[str, Any]:
    data = question.model_dump(by_alias=True, mode="json", exclude_none=True)
    shown = {k: v for k, v in data.items() if k not in _HIDDEN_QUESTION_KEYS}
    if "options" in shown:
        shown["options"] = [
            {k: v for k, v in option.items() if k not in _HIDDEN_OPTION_KEYS}
            for option in shown["options"]
        ]
    return shown


def _options(options: list[QuizOption]) -> tuple[OptionSpec, ...]:
    return tuple(OptionSpec(o.id, tuple(o.tags), o.branch, bool(o.exclusive)) for o in options)


def _rules(derived: list[DerivedTag]) -> tuple[Any, ...]:
    return tuple(parse_derived_rule(d.if_, d.add) for d in derived)


def _question(q: QuizQuestion) -> QuestionSpec:
    display = _display(q)
    if isinstance(q, InterstitialQuestion):
        return QuestionSpec(q.id, "interstitial", display)
    if isinstance(q, SingleQuestion):
        return QuestionSpec(
            q.id, "single", display, bool(q.health_data), options=_options(q.options)
        )
    if isinstance(q, MultiQuestion):
        return QuestionSpec(
            q.id,
            "multi",
            display,
            bool(q.health_data),
            bool(q.skippable),
            max_choices=q.max,
            options=_options(q.options),
        )
    if isinstance(q, GridQuestion):
        return QuestionSpec(
            q.id,
            "grid",
            display,
            row_ids=tuple(r.id for r in q.rows),
            state_ids=tuple(s.id for s in q.states),
            derived_rules=_rules(q.derived_tags),
        )
    return QuestionSpec(
        q.id,
        "scale",
        display,
        scale_min=q.min,
        scale_max=q.max,
        derived_rules=_rules(q.derived_tags),
    )
