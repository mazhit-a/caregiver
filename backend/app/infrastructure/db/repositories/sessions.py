"""Postgres repositories for sessions and active days."""

from datetime import date
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.session.entities import Session
from app.infrastructure.db.mappers import session_to_domain, session_to_row
from app.infrastructure.db.orm_models import ActiveDayRow, SessionRow


class SqlSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, session: Session) -> None:
        self._db.add(session_to_row(session))
        await self._db.flush()

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        result = await self._db.execute(
            select(SessionRow).where(SessionRow.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return session_to_domain(row) if row else None

    async def save(self, session: Session) -> None:
        await self._db.execute(
            update(SessionRow)
            .where(SessionRow.id == session.id)
            .values(
                clock_offset=session.clock_offset,
                last_seen_at=session.last_seen_at,
                recipient_key=session.recipient_key,
                display_name=session.display_name,
            )
        )


class SqlActiveDayRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(self, session_id: UUID, day: date) -> bool:
        stmt = (
            insert(ActiveDayRow)
            .values(session_id=session_id, day=day)
            .on_conflict_do_nothing()
            .returning(ActiveDayRow.day)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_days(self, session_id: UUID) -> list[date]:
        result = await self._db.execute(
            select(ActiveDayRow.day)
            .where(ActiveDayRow.session_id == session_id)
            .order_by(ActiveDayRow.day)
        )
        return list(result.scalars())
