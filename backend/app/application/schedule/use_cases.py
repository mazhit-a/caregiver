"""Schedule use cases: create at subscription start, extend on read."""

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from app.application.ports import UnitOfWork
from app.domain.schedule.entities import (
    LessonSchedule,
    PlanLessonRef,
    ScheduledLesson,
    UnlockRule,
)


class EnsureSchedule:
    """Idempotent: schedules built plan lessons that have no row yet, never moving existing ones.

    Called with the subscription start day when the subscription starts and again on every plan
    read, so lessons that become built later are appended after the last scheduled date.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        session_id: UUID,
        start_day: date,
        per_week: int,
        plan_lessons: Sequence[PlanLessonRef],
        rule: UnlockRule,
    ) -> list[ScheduledLesson]:
        built_ids = [lesson.lesson_id for lesson in plan_lessons if lesson.built]
        async with self._uow:
            existing = await self._uow.lesson_schedule.list_for_session(session_id)
            added = LessonSchedule.append_new(existing, built_ids, per_week, start_day, rule)
            if added:
                await self._uow.lesson_schedule.add_many(session_id, added)
                await self._uow.commit()
        return sorted([*existing, *added], key=lambda s: s.seq)
