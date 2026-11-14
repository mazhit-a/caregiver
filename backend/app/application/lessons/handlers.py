"""Answer handlers: one per screen type, found through `SCREEN_HANDLERS`.

A handler validates the value against the screen as the learner sees it, looks up the
server-only data (verdict, feedback, response, correctness, `storeAs`) in the lesson content
and returns an `AnswerOutcome`. It does no I/O; the use case persists the outcome. A new screen
type needs one entry in the registry.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from app.domain.lessons.errors import InvalidScreenAnswer
from app.domain.lessons.plans import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    IF_THEN_RESPONSE_MAX,
    IfThenPlan,
    Task,
    next_evening,
)
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
    lesson: Json = field(default_factory=dict)  # the rendered lesson (all screens, server data)
    screen_answers: Json = field(default_factory=dict)  # what the learner stored so far
    timezone: str = "UTC"
    is_first_lesson: bool = False
    app_url: str = ""


@dataclass(frozen=True)
class ConfidenceUpdate:
    """Ratings to save into `confidence.first` or `confidence.latest`."""

    slot: Literal["first", "latest"]
    ratings: dict[str, int]


@dataclass(frozen=True)
class AnswerOutcome:
    """What the answer changes. `result` goes to the client (camelCase keys); `stored` is
    merged into `LessonProgress.screen_answers`; `variant` is set only by the setup question."""

    result: dict[str, Any]
    stored: dict[str, Any] = field(default_factory=dict)
    variant: str | None = None
    scenario_answer: ScenarioAnswer | None = None
    if_then_plan: IfThenPlan | None = None
    task: Task | None = None
    confidence: ConfidenceUpdate | None = None


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


def _plan(ctx: AnswerContext, value: object) -> AnswerOutcome:
    """Value `{"response": str, "reminderDownloaded"?: bool}`. Saves the if-then plan and the
    do-now task; returns what the browser needs to build the reminder (.ics)."""
    screen = ctx.screen
    screen_id = screen["id"]
    if not isinstance(value, dict) or not isinstance(value.get("response"), str):
        raise InvalidScreenAnswer(screen_id, "value_must_be_an_object_with_response")
    downloaded = value.get("reminderDownloaded", False)
    if not isinstance(downloaded, bool):
        raise InvalidScreenAnswer(screen_id, "reminder_downloaded_must_be_boolean")
    response = value["response"].strip()
    if not response:
        raise InvalidScreenAnswer(screen_id, "response_required")
    if len(response) > IF_THEN_RESPONSE_MAX:
        raise InvalidScreenAnswer(screen_id, "response_too_long")
    if_then = screen["ifThen"]
    cue = pick(if_then["cueByVariant"], ctx.variant, if_then["cueVariantMap"])
    reset = _reset_label(ctx, if_then["resetFrom"])
    do_now = pick(screen["doNow"]["byVariant"], ctx.variant)
    plan = IfThenPlan(ctx.session_id, ctx.lesson_id, cue, response, reset, ctx.answered_at)
    task = Task(
        ctx.session_id, ctx.lesson_id, do_now["text"], do_now["action"], downloaded, ctx.answered_at
    )
    starts_at = next_evening(ctx.answered_at, ctx.timezone)
    result = {
        "ifThen": {"cue": cue, "response": response, "reset": reset},
        "task": {"text": task.text, "action": task.action},
        "reminder": {
            "title": screen["title"],
            "description": f"{cue} {if_then['responseLabel']} {response}\n{task.text}",
            "startsAt": starts_at.isoformat(),
            "timezone": ctx.timezone,
            "url": f"{ctx.app_url.rstrip('/')}/lessons/{ctx.lesson_id}",
        },
    }
    return AnswerOutcome(
        result,
        {screen_id: {"response": response, "reminderDownloaded": downloaded}},
        if_then_plan=plan,
        task=task,
    )


def _reset_label(ctx: AnswerContext, source_screen_id: str) -> str | None:
    """The label of the reset option the learner picked on the `resetFrom` mini-task."""
    chosen = ctx.screen_answers.get(source_screen_id)
    source = next((s for s in ctx.lesson.get("screens", []) if s["id"] == source_screen_id), None)
    if chosen is None or source is None:
        return None
    options = source.get("miniTask", {}).get("options", [])
    return next((o["label"] for o in options if o["id"] == chosen), None)


def _wrap(ctx: AnswerContext, value: object) -> AnswerOutcome:
    """Value `{itemId: 1..5}` for every item of the confidence check. The first lesson's check
    is saved as `first`, a later lesson's as `latest`."""
    screen_id = ctx.screen["id"]
    check = ctx.screen.get("confidenceCheck")
    if check is None or not (ctx.is_first_lesson or not check["onlyFirstLesson"]):
        raise InvalidScreenAnswer(screen_id, "screen_takes_no_answer")
    if not isinstance(value, dict) or set(value) != {i["id"] for i in check["items"]}:
        raise InvalidScreenAnswer(screen_id, "value_must_rate_every_item")
    for rating in value.values():
        if not isinstance(rating, int) or isinstance(rating, bool):
            raise InvalidScreenAnswer(screen_id, "rating_must_be_an_integer")
        if not CONFIDENCE_MIN <= rating <= CONFIDENCE_MAX:
            raise InvalidScreenAnswer(screen_id, "rating_out_of_range")
    ratings = {str(k): int(v) for k, v in value.items()}
    slot: Literal["first", "latest"] = "first" if ctx.is_first_lesson else "latest"
    return AnswerOutcome(
        {"saved": True, "ratings": ratings},
        {screen_id: ratings},
        confidence=ConfidenceUpdate(slot, ratings),
    )


SCREEN_HANDLERS: dict[str, ScreenHandler] = {
    "setup_question": _setup,
    "scenario": _scenario,
    "learn": _learn,
    "plan": _plan,
    "wrap": _wrap,
}
