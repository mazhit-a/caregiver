"""Postgres repository for role-play runs (scores and goals only; the table has no text)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.roleplay.run import RoleplayRun, RunContext, RunMode, RunRecord
from app.domain.roleplay.verdict import Goals
from app.infrastructure.db.orm_models import RoleplayRunRow


class SqlRoleplayRunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, run_id: UUID) -> RunRecord | None:
        result = await self._db.execute(select(RoleplayRunRow).where(RoleplayRunRow.id == run_id))
        row = result.scalar_one_or_none()
        return None if row is None else _to_record(row)

    async def list_finished(self, session_id: UUID) -> list[RunRecord]:
        result = await self._db.execute(
            select(RoleplayRunRow)
            .where(RoleplayRunRow.session_id == session_id, RoleplayRunRow.finished_at.is_not(None))
            .order_by(RoleplayRunRow.finished_at, RoleplayRunRow.started_at)
        )
        return [_to_record(row) for row in result.scalars()]

    async def save(self, record: RunRecord) -> None:
        values = {
            "mode": record.run.mode.value,
            "turn_scores": list(record.run.turn_scores),
            "goals_hit": [
                {"notice": g.notice, "reassure": g.reassure, "offer": g.offer}
                for g in record.run.goals_hit
            ],
            "finished_at": record.finished_at,
        }
        stmt = insert(RoleplayRunRow).values(
            id=record.id,
            session_id=record.session_id,
            lesson_id=record.lesson_id,
            context=record.context.value,
            variant=record.variant,
            rounds_total=record.run.rounds_total,
            started_at=record.started_at,
            **values,
        )
        await self._db.execute(
            stmt.on_conflict_do_update(index_elements=[RoleplayRunRow.id], set_=values)
        )


def _to_record(row: RoleplayRunRow) -> RunRecord:
    run = RoleplayRun(
        rounds_total=row.rounds_total,
        mode=RunMode(row.mode),
        turn_scores=list(row.turn_scores),
        goals_hit=[Goals(g["notice"], g["reassure"], g["offer"]) for g in row.goals_hit],
    )
    return RunRecord(
        id=row.id,
        session_id=row.session_id,
        lesson_id=row.lesson_id,
        context=RunContext(row.context),
        variant=row.variant,
        started_at=row.started_at,
        run=run,
        finished_at=row.finished_at,
    )
