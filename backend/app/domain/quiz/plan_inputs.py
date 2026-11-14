"""What the plan builder needs from the saved quiz answers (kept out of the plan domain)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.domain.plan.entities import HeardFragment
from app.domain.quiz.definition import CHANGES_QUESTION_ID, QuizDefinition
from app.domain.quiz.tags import chosen_options


@dataclass(frozen=True)
class PlanInputs:
    heard: tuple[HeardFragment, ...]  # "What we heard" fragments in question and answer order
    q5_order: tuple[str, ...]  # tags of the Q5 answers in the order chosen (gift phrases only)


def plan_inputs(definition: QuizDefinition, answers: Mapping[str, Any]) -> PlanInputs:
    heard: list[HeardFragment] = []
    q5_order: list[str] = []
    for spec in definition.questions:
        answer = answers.get(spec.id)
        if not spec.answerable or answer is None:
            continue
        for option in chosen_options(spec, answer):
            if spec.id == CHANGES_QUESTION_ID:
                q5_order.extend(option.tags)
            elif option.heard_slot is not None and option.heard_text is not None:
                heard.append(HeardFragment(option.heard_slot, option.heard_text))
    return PlanInputs(tuple(heard), tuple(q5_order))
