"""Validate and normalise one answer against its question."""

from typing import Any

from app.domain.quiz.definition import QuestionSpec
from app.domain.quiz.errors import InvalidAnswer


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def normalize_answer(spec: QuestionSpec, value: Any) -> Any:
    """Return the value to store (skipped -> None) or raise InvalidAnswer."""
    if _empty(value):
        if spec.skippable:
            return [] if spec.kind == "multi" else None
        raise InvalidAnswer("This question needs an answer.", {"questionId": spec.id})
    if spec.kind == "single":
        return _single(spec, value)
    if spec.kind == "multi":
        return _multi(spec, value)
    if spec.kind == "grid":
        return _grid(spec, value)
    return _scale(spec, value)


def _invalid(spec: QuestionSpec, message: str, **details: Any) -> InvalidAnswer:
    return InvalidAnswer(message, {"questionId": spec.id, **details})


def _single(spec: QuestionSpec, value: Any) -> str:
    if not isinstance(value, str) or spec.option(value) is None:
        raise _invalid(spec, "Pick one of the listed options.")
    return value


def _multi(spec: QuestionSpec, value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _invalid(spec, "Send a list of option ids.")
    chosen = list(dict.fromkeys(value))
    unknown = [v for v in chosen if spec.option(v) is None]
    if unknown:
        raise _invalid(spec, "Pick only the listed options.", unknown=unknown)
    if spec.max_choices is not None and len(chosen) > spec.max_choices:
        raise _invalid(spec, f"Pick at most {spec.max_choices}.", max=spec.max_choices)
    exclusive = next((v for v in chosen if (o := spec.option(v)) and o.exclusive), None)
    return [exclusive] if exclusive is not None else chosen


def _grid(spec: QuestionSpec, value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise _invalid(spec, "Send one state for every row.")
    if set(value) != set(spec.row_ids):
        raise _invalid(spec, "Send one state for every row.", rows=list(spec.row_ids))
    if any(state not in spec.state_ids for state in value.values()):
        raise _invalid(spec, "Pick one of the listed states.", states=list(spec.state_ids))
    return {row: value[row] for row in spec.row_ids}


def _scale(spec: QuestionSpec, value: Any) -> int:
    low, high = spec.scale_min, spec.scale_max
    if isinstance(value, bool) or not isinstance(value, int):
        raise _invalid(spec, "Send a whole number.")
    if low is None or high is None or not low <= value <= high:
        raise _invalid(spec, f"Pick a number from {low} to {high}.", min=low, max=high)
    return value
