"""Postgres repository for the confidence ratings of a session (day 0 now; more later)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm_models import ConfidenceRow


class SqlConfidenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_day0(self, session_id: UUID) -> int | None:
        result = await self._db.execute(
            select(ConfidenceRow.day0).where(ConfidenceRow.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def save_day0(self, session_id: UUID, value: int) -> None:
        stmt = insert(ConfidenceRow).values(session_id=session_id, day0=value)
        await self._db.execute(
            stmt.on_conflict_do_update(
                index_elements=[ConfidenceRow.session_id], set_={"day0": value}
            )
        )
