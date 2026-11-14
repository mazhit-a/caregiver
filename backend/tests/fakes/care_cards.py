from uuid import UUID

from app.domain.care_card.entities import CareCard


class InMemoryCareCardRepository:
    def __init__(self) -> None:
        self.rows: dict[str, CareCard] = {}

    async def get(self, card_id: str) -> CareCard | None:
        return self.rows.get(card_id)

    async def get_current(self, session_id: UUID) -> CareCard | None:
        mine = [c for c in self.rows.values() if c.session_id == session_id]
        live = [c for c in mine if not c.is_revoked]
        if live:
            return live[0]
        revoked = sorted(mine, key=lambda c: c.revoked_at or c.published_at)
        return revoked[-1] if revoked else None

    async def save(self, card: CareCard) -> None:
        self.rows[card.id] = card
