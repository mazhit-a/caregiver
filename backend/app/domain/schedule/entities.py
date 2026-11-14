"""Lesson schedule: unlock dates from the pace formula, lesson status, and the hero lesson.

Pure and clock-free: every date (start day, today) is passed in.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from app.domain.plan.entities import PaceRules

LessonStatus = Literal["locked", "available", "in_progress", "done", "coming_later"]


@dataclass(frozen=True)
class UnlockRule:
    """`offset(k) = ceil(k * days_per_week / per_week) + first_lesson_offset_days`."""

    days_per_week: int
    first_lesson_offset_days: int

    @classmethod
    def from_pace(cls, pace: PaceRules) -> "UnlockRule":
        return cls(pace.unlock_days_per_week, pace.unlock_first_lesson_offset_days)

    def offset_days(self, k: int, per_week: int) -> int:
        if per_week <= 0:
            raise ValueError("per_week must be positive")
        # integer ceiling division
        return -(-k * self.days_per_week // per_week) + self.first_lesson_offset_days


@dataclass(frozen=True)
class ScheduledLesson:
    lesson_id: str
    seq: int  # 0-based position among the built lessons, in plan order
    unlock_on: date


@dataclass(frozen=True)
class PlanLessonRef:
    lesson_id: str
    built: bool


@dataclass(frozen=True)
class LessonState:
    lesson_id: str
    status: LessonStatus
    unlock_on: date | None  # None for lessons that are not scheduled (coming_later)


class LessonSchedule:
    """Stateless domain logic over `ScheduledLesson` rows."""

    @staticmethod
    def unlock_dates(
        start_day: date, per_week: int, lesson_ids: Sequence[str], rule: UnlockRule
    ) -> list[ScheduledLesson]:
        """Dates for built lessons only, in plan order, from `start_day`."""
        return [
            ScheduledLesson(lesson_id, k, start_day + timedelta(days=rule.offset_days(k, per_week)))
            for k, lesson_id in enumerate(lesson_ids)
        ]

    @staticmethod
    def append_new(
        existing: Sequence[ScheduledLesson],
        built_lesson_ids: Sequence[str],
        per_week: int,
        start_day: date,
        rule: UnlockRule,
    ) -> list[ScheduledLesson]:
        """Schedule built lessons not yet scheduled after the last date, at the same pace.

        Existing rows are never changed. With nothing scheduled yet, this is `unlock_dates`.
        """
        scheduled = {s.lesson_id for s in existing}
        new_ids = [i for i in built_lesson_ids if i not in scheduled]
        if not existing:
            return LessonSchedule.unlock_dates(start_day, per_week, new_ids, rule)
        last = max(existing, key=lambda s: s.seq)
        last_date = max(s.unlock_on for s in existing)
        return [
            ScheduledLesson(
                lesson_id,
                last.seq + 1 + j,
                last_date
                + timedelta(days=rule.offset_days(j + 1, per_week) - rule.offset_days(0, per_week)),
            )
            for j, lesson_id in enumerate(new_ids)
        ]

    @staticmethod
    def statuses(
        plan_lessons: Sequence[PlanLessonRef],
        schedule: Sequence[ScheduledLesson],
        today: date,
        done_ids: Collection[str],
        in_progress_ids: Collection[str],
    ) -> list[LessonState]:
        """Status per plan lesson, in plan order."""
        unlock_by_id = {s.lesson_id: s.unlock_on for s in schedule}
        states: list[LessonState] = []
        for lesson in plan_lessons:
            unlock_on = unlock_by_id.get(lesson.lesson_id)
            if not lesson.built or unlock_on is None:
                states.append(LessonState(lesson.lesson_id, "coming_later", None))
            elif lesson.lesson_id in done_ids:
                states.append(LessonState(lesson.lesson_id, "done", unlock_on))
            elif unlock_on > today:
                states.append(LessonState(lesson.lesson_id, "locked", unlock_on))
            elif lesson.lesson_id in in_progress_ids:
                states.append(LessonState(lesson.lesson_id, "in_progress", unlock_on))
            else:
                states.append(LessonState(lesson.lesson_id, "available", unlock_on))
        return states

    @staticmethod
    def hero_lesson_id(states: Sequence[LessonState]) -> str | None:
        """First unlocked lesson (available or in progress) that is not done, in plan order."""
        for state in states:
            if state.status in ("available", "in_progress"):
                return state.lesson_id
        return None
