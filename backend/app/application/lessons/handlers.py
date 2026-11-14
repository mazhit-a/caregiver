"""Answer handlers: one per screen type, found through `SCREEN_HANDLERS`.

A handler validates the value against the screen as the learner sees it, looks up the
server-only data (verdict, feedback, response, correctness, `storeAs`) in the lesson content
and returns an `AnswerOutcome`. It does no I/O; the use case persists the outcome. A new screen
type needs one entry in the registry.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.domain.lessons.errors import InvalidScreenAnswer
from app.domain.lessons.progress import ScenarioAnswer
from app.domain.lessons.variants import pick

Json = Mapping[str, Any]
VARIANT_KEY = "variant"


@dataclass(frozen=True)
class AnswerContext:
    session_id: UUID
    lesson_id: str
    screen: Json
    variant: str | None
    answered_at: datetime


@dataclass(frozen=True)
class AnswerOutcome:
    """What the answer changes. `result` goes to the client (camelCase keys); `stored` is
    merged into `LessonProgress.screen_answers`; `variant` is set only by the setup question."""

    result: dict[str, Any]
    stored: dict[str, Any] = field(default_factory=dict)
    variant: str | None = None
    scenario_answer: ScenarioAnswer | None = None


class ScreenHandler(Protocol):
    def __call__(self, ctx: AnswerContext, value: object) -> AnswerOutcome: ...


def _option_id(screen_id: str, value: object) -> str:
    if not isinstance(value, str):
        raise InvalidScreenAnswer(screen_id, "value_must_be_an_option_id")
    return value


def _find(screen_id: str, options: list[Json], option_id: str) -> Json:
    for option in options:
        if option["id"] == option_id:
            return option
    raise InvalidScreenAnswer(screen_id, "option_not_on_screen")


def _setup(ctx: AnswerContext, value: object) -> AnswerOutcome:
    screen_id = ctx.screen["id"]
    option = _find(screen_id, ctx.screen["options"], _option_id(screen_id, value))
    stored = {screen_id: option["id"]}
    # The variant only selects wording and examples; the plan and schedule are not touched.
    if ctx.screen.get("storeAs") == VARIANT_KEY:
        return AnswerOutcome({VARIANT_KEY: option["id"]}, stored, variant=option["id"])
    return AnswerOutcome({}, stored)


def _scenario(ctx: AnswerContext, value: object) -> AnswerOutcome:
    screen = ctx.screen
    answers = pick(screen["answers"], ctx.variant, screen["answersVariantMap"])
    answer = _find(screen["id"], answers, _option_id(screen["id"], value))
    record = ScenarioAnswer(
        ctx.session_id,
        ctx.lesson_id,
        screen["id"],
        answer["id"],
        answer["verdict"],
        ctx.answered_at,
    )
    result = {
        "answerId": answer["id"],
        "verdict": answer["verdict"],
        "feedback": answer["feedback"],
        "savePhrase": answer.get("savePhrase") is True,
    }
    return AnswerOutcome(result, {screen["id"]: answer["id"]}, scenario_answer=record)


def _learn(ctx: AnswerContext, value: object) -> AnswerOutcome:
    screen_id = ctx.screen["id"]
    task = ctx.screen.get("miniTask")
    if task is None:
        raise InvalidScreenAnswer(screen_id, "screen_takes_no_answer")
    option = _find(screen_id, task["options"], _option_id(screen_id, value))
    result: dict[str, Any] = {"optionId": option["id"], "response": option.get("response")}
    if "correct" in option:
        result["correct"] = option["correct"]
    stored: dict[str, Any] = {screen_id: option["id"]}
    if task.get("storeAs"):
        stored[task["storeAs"]] = option["id"]
    return AnswerOutcome(result, stored)


SCREEN_HANDLERS: dict[str, ScreenHandler] = {
    "setup_question": _setup,
    "scenario": _scenario,
    "learn": _learn,
}
