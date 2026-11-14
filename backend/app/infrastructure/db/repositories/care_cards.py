"""Postgres repository for care cards (live rows and tombstones)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.care_card.entities import CardSnapshot, CareCard
from app.infrastructure.db.orm_models import CareCardRow


class SqlCareCardRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, card_id: str) -> CareCard | None:
        row = await self._db.get(CareCardRow, card_id)
        return None if row is None else _card(row)

    async def get_current(self, session_id: UUID) -> CareCard | None:
        base = select(CareCardRow).where(CareCardRow.session_id == session_id)
        live = await self._db.execute(base.where(CareCardRow.revoked_at.is_(None)).limit(1))
        row = live.scalars().first()
        if row is None:
            revoked = await self._db.execute(base.order_by(CareCardRow.revoked_at.desc()).limit(1))
            row = revoked.scalars().first()
        return None if row is None else _card(row)

    async def save(self, card: CareCard) -> None:
        row = await self._db.get(CareCardRow, card.id)
        if row is None:
            row = CareCardRow(id=card.id, session_id=card.session_id)
            self._db.add(row)
        row.snapshot = None if card.snapshot is None else card.snapshot.to_json()
        row.phrase_ids = [str(p) for p in card.phrase_ids]
        row.published_at = card.published_at
        row.updated_at = card.updated_at
        row.revoked_at = card.revoked_at
        row.last_opened_at = card.last_opened_at


def _card(row: CareCardRow) -> CareCard:
    return CareCard(
        row.id,
        row.session_id,
        None if row.snapshot is None else CardSnapshot.from_json(row.snapshot),
        tuple(UUID(p) for p in row.phrase_ids),
        row.published_at,
        row.updated_at,
        row.revoked_at,
        row.last_opened_at,
    )
