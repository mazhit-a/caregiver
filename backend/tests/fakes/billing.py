from copy import copy
from uuid import UUID

from app.domain.billing.entities import Subscription, SubscriptionHistoryEntry


def _snapshot(subscription: Subscription) -> Subscription:
    clone = copy(subscription)
    clone._pending = []
    return clone


class InMemorySubscriptionRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, Subscription] = {}
        self.saves: list[Subscription] = []  # every save, in order (snapshots)

    async def get(self, session_id: UUID) -> Subscription | None:
        stored = self.rows.get(session_id)
        return _snapshot(stored) if stored else None

    async def save(self, subscription: Subscription) -> None:
        self.rows[subscription.session_id] = _snapshot(subscription)
        self.saves.append(_snapshot(subscription))


class InMemorySubscriptionHistoryRepository:
    def __init__(self) -> None:
        self.entries: list[SubscriptionHistoryEntry] = []

    async def add(self, entry: SubscriptionHistoryEntry) -> None:
        self.entries.append(entry)

    async def list_for_session(self, session_id: UUID) -> list[SubscriptionHistoryEntry]:
        return [e for e in self.entries if e.session_id == session_id]
