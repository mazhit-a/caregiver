"""Postgres repositories for the if-then plan and the do-now task of a lesson."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.plans import IfThenPlan, Task
from app.infrastructure.db.orm_models import IfThenPlanRow, TaskRow


class SqlIfThenPlanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID, lesson_id: str) -> IfThenPlan | None:
        result = await self._db.execute(
            select(IfThenPlanRow).where(
                IfThenPlanRow.session_id == session_id, IfThenPlanRow.lesson_id == lesson_id
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return IfThenPlan(
            row.session_id, row.lesson_id, row.cue, row.response, row.reset, row.created_at
        )

    async def save(self, plan: IfThenPlan) -> None:
        values = {"cue": plan.cue, "response": plan.response, "reset": plan.reset}
        stmt = insert(IfThenPlanRow).values(
            session_id=plan.session_id,
            lesson_id=plan.lesson_id,
            created_at=plan.created_at,
            **values,
        )
        await self._db.execute(
            stmt.on_conflict_do_update(
                index_elements=[IfThenPlanRow.session_id, IfThenPlanRow.lesson_id], set_=values
            )
        )


class SqlTaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID, lesson_id: str) -> Task | None:
        result = await self._db.execute(
            select(TaskRow).where(TaskRow.session_id == session_id, TaskRow.lesson_id == lesson_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return Task(
            row.session_id,
            row.lesson_id,
            row.text,
            row.action,
            row.reminder_downloaded,
            row.created_at,
            row.done_at,
        )

    async def save(self, task: Task) -> None:
        """A new answer replaces text, action and the download flag; `done_at` is kept."""
        values = {
            "text": task.text,
            "action": task.action,
            "reminder_downloaded": task.reminder_downloaded,
        }
        stmt = insert(TaskRow).values(
            session_id=task.session_id,
            lesson_id=task.lesson_id,
            created_at=task.created_at,
            done_at=task.done_at,
            **values,
        )
        await self._db.execute(
            stmt.on_conflict_do_update(
                index_elements=[TaskRow.session_id, TaskRow.lesson_id], set_=values
            )
        )
