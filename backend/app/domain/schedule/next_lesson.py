"""The next lesson to recommend (Skills now, Today later): one selection rule, one place."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.plan.entities import PlanModule
from app.domain.schedule.entities import LessonSchedule, LessonState, LessonStatus


@dataclass(frozen=True)
class NextLesson:
    """`status` is `available` or `in_progress` for the hero lesson, `locked` when nothing is
    unlocked yet (then `unlock_on` says when). `reason` is the reason of the lesson's module."""

    lesson_id: str
    title: str
    module_id: str
    reason: str
    status: LessonStatus
    unlock_on: date | None


def select_next_lesson(
    modules: Sequence[PlanModule], states: Sequence[LessonState]
) -> NextLesson | None:
    """The hero lesson (first unlocked lesson that is not done); else the earliest locked one;
    else None (everything built is done)."""
    by_id = {s.lesson_id: s for s in states}
    hero_id = LessonSchedule.hero_lesson_id(states)
    chosen: LessonState | None = None if hero_id is None else by_id[hero_id]
    if chosen is None:
        locked = [s for s in states if s.status == "locked" and s.unlock_on is not None]
        chosen = min(locked, key=lambda s: s.unlock_on or date.max, default=None)
    if chosen is None:
        return None
    for module in modules:
        for lesson in module.lessons:
            if lesson.id == chosen.lesson_id:
                return NextLesson(
                    lesson.id,
                    lesson.title,
                    module.id,
                    module.reason,
                    chosen.status,
                    chosen.unlock_on,
                )
    return None
