"""Postgres repository for the confidence ratings of a session (day 0, first and latest)."""

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lessons.plans import ConfidenceRatings
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

    async def get_ratings(self, session_id: UUID) -> ConfidenceRatings:
        result = await self._db.execute(
            select(ConfidenceRow.first, ConfidenceRow.latest).where(
                ConfidenceRow.session_id == session_id
            )
        )
        row = result.one_or_none()
        return ConfidenceRatings() if row is None else ConfidenceRatings(row.first, row.latest)

    async def save_ratings(
        self, session_id: UUID, slot: Literal["first", "latest"], ratings: dict[str, int]
    ) -> None:
        stmt = insert(ConfidenceRow).values(session_id=session_id, **{slot: ratings})
        await self._db.execute(
            stmt.on_conflict_do_update(
                index_elements=[ConfidenceRow.session_id], set_={slot: ratings}
            )
        )
