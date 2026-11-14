"""Postgres repository for the per-session lesson schedule."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schedule.entities import ScheduledLesson
from app.infrastructure.db.orm_models import LessonScheduleRow


class SqlLessonScheduleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_session(self, session_id: UUID) -> list[ScheduledLesson]:
        result = await self._db.execute(
            select(LessonScheduleRow)
            .where(LessonScheduleRow.session_id == session_id)
            .order_by(LessonScheduleRow.seq)
        )
        return [ScheduledLesson(r.lesson_id, r.seq, r.unlock_on) for r in result.scalars()]

    async def add_many(self, session_id: UUID, lessons: list[ScheduledLesson]) -> None:
        self._db.add_all(
            LessonScheduleRow(
                session_id=session_id, lesson_id=x.lesson_id, seq=x.seq, unlock_on=x.unlock_on
            )
            for x in lessons
        )
        await self._db.flush()
