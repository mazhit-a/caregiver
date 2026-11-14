"""Lesson rendering: variant applied, server-only data removed.

Input is the lesson as the content provider renders it (camelCase JSON, recipient placeholders
filled). Output holds only what the learner may see: scenario verdicts and feedback, mini-task
responses and correctness, `storeAs` keys, save flags and plan defaults stay on the server for
the answer handlers. Each screen type has one renderer in `SCREEN_RENDERERS`; a new screen type
needs one entry there.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.domain.lessons.variants import pick

Screen = dict[str, Any]
Json = Mapping[str, Any]

# Placeholders that only exist at the point of use (role-play results, recap of the previous
# lesson). The lesson read renders them as empty and drops the fields that contain them.
RUNTIME_PLACEHOLDERS = ("savedPhrase", "firstScore", "lastScore")
SETUP_SCREEN_TYPE = "setup_question"


@dataclass(frozen=True)
class RenderContext:
    variant: str | None
    pattern: Json
    is_first_lesson: bool


@dataclass(frozen=True)
class RenderedLesson:
    id: str
    module_id: str
    title: str
    minutes: int
    skill: str
    skill_label: str
    variant: str | None
    pattern: Json
    screens: list[Screen]


def _copy(source: Json, keys: tuple[str, ...]) -> Screen:
    return {key: source[key] for key in keys if key in source}


def _options(options: list[Json]) -> list[Screen]:
    return [_copy(option, ("id", "label")) for option in options]


def _setup(screen: Json, ctx: RenderContext) -> Screen:
    out = _copy(screen, ("id", "type", "speaker", "text", "question"))
    out["options"] = _options(screen["options"])
    return out


def _scenario(screen: Json, ctx: RenderContext) -> Screen:
    var_map = screen["answersVariantMap"]
    chosen = pick(screen["byVariant"], ctx.variant, var_map)
    out = _copy(screen, ("id", "type", "question", "verdictLabels", "afterChoice", "saveButton"))
    out.update(_copy(chosen, ("intro", "setup", "line")))
    out["answers"] = [
        _copy(answer, ("id", "text")) for answer in pick(screen["answers"], ctx.variant, var_map)
    ]
    return out


def _learn(screen: Json, ctx: RenderContext) -> Screen:
    out = _copy(screen, ("id", "type", "title", "body", "patternTip"))
    if "bullets" in screen:
        out["bullets"] = list(pick(screen["bullets"], ctx.variant, screen.get("bulletsVariantMap")))
    if ctx.variant == "both" and "extraForBoth" in screen:
        out["extra"] = screen["extraForBoth"]
    if screen.get("showPattern"):
        out["pattern"] = dict(ctx.pattern)
    if "miniTask" in screen:
        task = screen["miniTask"]
        out["miniTask"] = {
            "question": task["question"],
            "options": _options(task["options"]),
        }
    return out


def _roleplay(screen: Json, ctx: RenderContext) -> Screen:
    out = _copy(screen, ("id", "type", "title", "intro", "goals", "labels"))
    out["rounds"] = [
        _copy(r, ("stage", "line", "mood"))
        for r in pick(screen["roundsByVariant"], ctx.variant, screen["roundsVariantMap"])
    ]
    # `firstVsLast` holds {firstScore}/{lastScore}: it is rendered with the run's results later.
    out["summary"] = _copy(
        screen["summary"], ("title", "bestPhraseLabel", "saveButton", "againButton")
    )
    return out


def _plan(screen: Json, ctx: RenderContext) -> Screen:
    if_then = screen["ifThen"]
    do_now = pick(screen["doNow"]["byVariant"], ctx.variant)
    out = _copy(screen, ("id", "type", "title", "remindButton", "doneButton", "noteTemplate"))
    out["ifThen"] = {
        "cue": pick(if_then["cueByVariant"], ctx.variant, if_then["cueVariantMap"]),
        "responseLabel": if_then["responseLabel"],
        "responseEditable": if_then["responseEditable"],
        "resetLabel": if_then["resetLabel"],
        "resetFrom": if_then["resetFrom"],
    }
    out["doNow"] = {
        "title": screen["doNow"]["title"],
        **_copy(do_now, ("text", "action", "button")),
    }
    return out


def _wrap(screen: Json, ctx: RenderContext) -> Screen:
    out = _copy(
        screen, ("id", "type", "skillLine", "phraseLine", "patternLine", "tomorrowLine", "nextLine")
    )
    check = screen.get("confidenceCheck")
    if check is not None and (ctx.is_first_lesson or not check["onlyFirstLesson"]):
        out["confidenceCheck"] = {
            **_copy(check, ("title", "scale")),
            "items": _options(check["items"]),
        }
    return out


ScreenRenderer = Callable[[Json, RenderContext], Screen]

SCREEN_RENDERERS: dict[str, ScreenRenderer] = {
    "setup_question": _setup,
    "scenario": _scenario,
    "learn": _learn,
    "roleplay": _roleplay,
    "plan": _plan,
    "wrap": _wrap,
}


def render_lesson(lesson: Json, variant: str | None, is_first_lesson: bool) -> RenderedLesson:
    """The learner-facing lesson for the chosen variant.

    A lesson with a setup question but no chosen variant yet shows the screens up to and
    including that question only; the rest depends on the answer.
    """
    ctx = RenderContext(variant, lesson["pattern"], is_first_lesson)
    screens = visible_screens(lesson, variant)
    return RenderedLesson(
        id=lesson["id"],
        module_id=lesson["moduleId"],
        title=lesson["title"],
        minutes=lesson["minutes"],
        skill=lesson["skill"],
        skill_label=lesson["skillLabel"],
        variant=variant,
        pattern=lesson["pattern"],
        screens=[SCREEN_RENDERERS[s["type"]](s, ctx) for s in screens],
    )


def visible_screens(lesson: Json, variant: str | None) -> list[Json]:
    """The raw screens a learner can see: all of them, or up to the setup question until a
    variant is chosen."""
    screens: list[Json] = list(lesson["screens"])
    return screens if variant is not None else _until_setup(screens)


def _until_setup(screens: list[Json]) -> list[Json]:
    for index, screen in enumerate(screens):
        if screen["type"] == SETUP_SCREEN_TYPE:
            return screens[: index + 1]
    return screens
