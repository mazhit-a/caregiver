from uuid import UUID

from app.domain.phrases.entities import SavedPhrase


class InMemorySavedPhraseRepository:
    def __init__(self) -> None:
        self.rows: list[SavedPhrase] = []

    async def add(self, phrase: SavedPhrase) -> None:
        self.rows.append(phrase)

    async def count(self, session_id: UUID) -> int:
        return len([r for r in self.rows if r.session_id == session_id])

    async def list_for_session(self, session_id: UUID) -> list[SavedPhrase]:
        rows = [r for r in self.rows if r.session_id == session_id]
        return sorted(rows, key=lambda r: r.saved_at)

    async def delete(self, session_id: UUID, phrase_id: UUID) -> bool:
        kept = [r for r in self.rows if not (r.id == phrase_id and r.session_id == session_id)]
        removed = len(kept) != len(self.rows)
        self.rows = kept
        return removed
