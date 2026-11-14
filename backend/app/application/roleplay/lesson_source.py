"""Reads the role-play parts of a lesson: rounds by variant, labels and fallback scenarios."""

from typing import Any

from app.application.lessons.access import valid_variant
from app.application.ports import ContentProvider
from app.application.roleplay.dto import RoundView
from app.domain.lessons.errors import LessonContentError
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS
from app.domain.lessons.variants import pick
from app.domain.roleplay.run import RunContext
from app.domain.session.entities import Session

Json = dict[str, Any]


def render(
    content: ContentProvider,
    session: Session,
    lesson_id: str,
    variant: str | None,
    runtime: dict[str, str] | None = None,
) -> Json:
    """The rendered lesson; runtime placeholders are empty unless `runtime` gives them."""
    values = dict.fromkeys(RUNTIME_PLACEHOLDERS, "") | (runtime or {})
    return content.render_lesson(
        lesson_id,
        session.recipient_key or "",
        valid_variant(content, lesson_id, variant),
        runtime_values=values,
        display_name=session.display_name,
    )


def roleplay_screen(lesson: Json) -> Json:
    for screen in lesson["screens"]:
        if screen["type"] == "roleplay":
            found: Json = screen
            return found
    raise LessonContentError("The lesson has no role-play screen")


def rounds_for(lesson: Json, context: RunContext, variant: str | None) -> tuple[RoundView, ...]:
    """Lesson context: the role-play screen's rounds. Practice round: `day2.practiceRound`.
    Both go through their own `roundsVariantMap`."""
    block = (
        roleplay_screen(lesson) if context is RunContext.LESSON else lesson["day2"]["practiceRound"]
    )
    rounds = pick(block["roundsByVariant"], variant, block["roundsVariantMap"])
    return tuple(RoundView(r["stage"], r["line"], r["mood"]) for r in rounds)


def fallback_scenarios(lesson: Json) -> tuple[Json, ...]:
    """The lesson's fallback scenarios that the role-play screen lists, in its order."""
    wanted: list[str] = roleplay_screen(lesson)["fallbackScenarios"]
    by_id = {s["id"]: s for s in lesson["fallbackScenarios"]}
    return tuple(by_id[i] for i in wanted if i in by_id)
