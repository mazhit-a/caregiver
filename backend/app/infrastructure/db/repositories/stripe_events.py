"""Postgres repository of handled Stripe webhook events."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.orm_models import StripeEventRow


class SqlStripeEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def begin(self, event_id: str, event_type: str, received_at: datetime) -> bool:
        inserted = await self._db.execute(
            insert(StripeEventRow)
            .values(event_id=event_id, type=event_type, received_at=received_at)
            .on_conflict_do_nothing()
            .returning(StripeEventRow.event_id)
        )
        if inserted.scalar_one_or_none() is not None:
            return True
        processed_at = await self._db.scalar(
            select(StripeEventRow.processed_at).where(StripeEventRow.event_id == event_id)
        )
        return processed_at is None  # recorded earlier but never finished: handle it again

    async def mark_processed(self, event_id: str, processed_at: datetime) -> None:
        await self._db.execute(
            update(StripeEventRow)
            .where(StripeEventRow.event_id == event_id)
            .values(processed_at=processed_at)
        )
