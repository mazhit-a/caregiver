"""Postgres repository for lesson progress."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.progress import LessonProgress
from app.infrastructure.db.orm_models import LessonProgressRow


class SqlLessonProgressRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID, lesson_id: str) -> LessonProgress | None:
        result = await self._db.execute(
            select(LessonProgressRow).where(
                LessonProgressRow.session_id == session_id,
                LessonProgressRow.lesson_id == lesson_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return LessonProgress(
            session_id=row.session_id,
            lesson_id=row.lesson_id,
            started_at=row.started_at,
            variant=row.variant,
            step=row.step,
            screen_answers=dict(row.screen_answers),
            done_at=row.done_at,
        )

    async def save(self, progress: LessonProgress) -> None:
        values = {
            "variant": progress.variant,
            "step": progress.step,
            "screen_answers": progress.screen_answers,
            "started_at": progress.started_at,
            "done_at": progress.done_at,
        }
        stmt = insert(LessonProgressRow).values(
            session_id=progress.session_id, lesson_id=progress.lesson_id, **values
        )
        await self._db.execute(
            stmt.on_conflict_do_update(
                index_elements=[LessonProgressRow.session_id, LessonProgressRow.lesson_id],
                set_=values,
            )
        )
