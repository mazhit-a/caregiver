"""Tags and branch derived from the saved answers."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.domain.quiz.definition import OptionSpec, QuestionSpec, QuizDefinition


@dataclass(frozen=True)
class DerivedQuiz:
    tags: tuple[str, ...]
    branch: str | None


def derive(definition: QuizDefinition, answers: Mapping[str, Any]) -> DerivedQuiz:
    """Tags in question order (option tags, then derived tags), no duplicates; branch from Q3."""
    tags: list[str] = []
    branch: str | None = None
    for spec in definition.questions:
        answer = answers.get(spec.id)
        if not spec.answerable or answer is None:
            continue
        for option in chosen_options(spec, answer):
            tags.extend(option.tags)
            branch = option.branch or branch
        tags.extend(rule.add for rule in spec.derived_rules if rule.matches(answer))
    return DerivedQuiz(tuple(dict.fromkeys(tags)), branch)


def chosen_options(spec: QuestionSpec, answer: Any) -> list[OptionSpec]:
    if spec.kind == "single" and isinstance(answer, str):
        found = spec.option(answer)
        return [found] if found else []
    if spec.kind == "multi" and isinstance(answer, list):
        return [o for v in answer if (o := spec.option(v)) is not None]
    return []
