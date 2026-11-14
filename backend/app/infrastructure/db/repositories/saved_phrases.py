"""Postgres repository for saved phrases."""

from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.phrases.entities import PhraseSource, SavedPhrase
from app.infrastructure.db.orm_models import SavedPhraseRow


class SqlSavedPhraseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, phrase: SavedPhrase) -> None:
        self._db.add(
            SavedPhraseRow(
                id=phrase.id,
                session_id=phrase.session_id,
                text=phrase.text,
                source=phrase.source,
                lesson_id=phrase.lesson_id,
                saved_at=phrase.saved_at,
            )
        )

    async def count(self, session_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(SavedPhraseRow)
            .where(SavedPhraseRow.session_id == session_id)
        )
        return int(result.scalar_one())

    async def list_for_session(self, session_id: UUID) -> list[SavedPhrase]:
        result = await self._db.execute(
            select(SavedPhraseRow)
            .where(SavedPhraseRow.session_id == session_id)
            .order_by(SavedPhraseRow.saved_at, SavedPhraseRow.id)
        )
        return [
            SavedPhrase(
                row.id,
                row.session_id,
                row.text,
                cast(PhraseSource, row.source),
                row.lesson_id,
                row.saved_at,
            )
            for row in result.scalars()
        ]

    async def delete(self, session_id: UUID, phrase_id: UUID) -> bool:
        result = await self._db.execute(
            delete(SavedPhraseRow).where(
                SavedPhraseRow.id == phrase_id, SavedPhraseRow.session_id == session_id
            )
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]
