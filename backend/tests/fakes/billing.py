from copy import copy
from datetime import datetime
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

    async def get_by_stripe_customer_id(self, customer_id: str) -> Subscription | None:
        for stored in self.rows.values():
            if stored.stripe_customer_id == customer_id:
                return _snapshot(stored)
        return None

    async def get_by_stripe_test_clock_id(self, test_clock_id: str) -> Subscription | None:
        for stored in self.rows.values():
            if stored.stripe_test_clock_id == test_clock_id:
                return _snapshot(stored)
        return None

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


class InMemoryStripeEventRepository:
    def __init__(self) -> None:
        self.events: dict[str, tuple[str, datetime, datetime | None]] = {}  # type, received, done

    async def begin(self, event_id: str, event_type: str, received_at: datetime) -> bool:
        if event_id not in self.events:
            self.events[event_id] = (event_type, received_at, None)
            return True
        return self.events[event_id][2] is None

    async def mark_processed(self, event_id: str, processed_at: datetime) -> None:
        event_type, received_at, _ = self.events[event_id]
        self.events[event_id] = (event_type, received_at, processed_at)
