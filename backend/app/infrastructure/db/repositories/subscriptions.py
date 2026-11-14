"""Postgres repositories for the subscription and its status history."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.entities import (
    BillingSync,
    Subscription,
    SubscriptionHistoryEntry,
    SubscriptionSource,
    SubscriptionStatus,
)
from app.infrastructure.db.orm_models import SubscriptionHistoryRow, SubscriptionRow


class SqlSubscriptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, session_id: UUID) -> Subscription | None:
        result = await self._db.execute(
            select(SubscriptionRow).where(SubscriptionRow.session_id == session_id)
        )
        return self._to_domain(result.scalar_one_or_none())

    async def get_by_stripe_customer_id(self, customer_id: str) -> Subscription | None:
        result = await self._db.execute(
            select(SubscriptionRow).where(SubscriptionRow.stripe_customer_id == customer_id)
        )
        return self._to_domain(result.scalars().first())

    async def get_by_stripe_test_clock_id(self, test_clock_id: str) -> Subscription | None:
        result = await self._db.execute(
            select(SubscriptionRow).where(SubscriptionRow.stripe_test_clock_id == test_clock_id)
        )
        return self._to_domain(result.scalars().first())

    @staticmethod
    def _to_domain(row: SubscriptionRow | None) -> Subscription | None:
        if row is None:
            return None
        return Subscription(
            session_id=row.session_id,
            status=cast(SubscriptionStatus, row.status),
            plan_id=row.plan_id,
            source=cast(SubscriptionSource | None, row.source),
            current_period_start=row.current_period_start,
            current_period_end=row.current_period_end,
            renewal_count=row.renewal_count,
            auto_renew_consent_at=row.auto_renew_consent_at,
            stripe_customer_id=row.stripe_customer_id,
            stripe_subscription_id=row.stripe_subscription_id,
            stripe_test_clock_id=row.stripe_test_clock_id,
            stripe_clock_at=row.stripe_clock_at,
            billing_sync=cast(BillingSync, row.billing_sync),
        )

    async def save(self, subscription: Subscription) -> None:
        values = {
            "status": subscription.status,
            "plan_id": subscription.plan_id,
            "source": subscription.source,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "renewal_count": subscription.renewal_count,
            "auto_renew_consent_at": subscription.auto_renew_consent_at,
            "stripe_customer_id": subscription.stripe_customer_id,
            "stripe_subscription_id": subscription.stripe_subscription_id,
            "stripe_test_clock_id": subscription.stripe_test_clock_id,
            "stripe_clock_at": subscription.stripe_clock_at,
            "billing_sync": subscription.billing_sync,
        }
        stmt = insert(SubscriptionRow).values(session_id=subscription.session_id, **values)
        await self._db.execute(
            stmt.on_conflict_do_update(index_elements=[SubscriptionRow.session_id], set_=values)
        )


class SqlSubscriptionHistoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(self, entry: SubscriptionHistoryEntry) -> None:
        self._db.add(
            SubscriptionHistoryRow(
                session_id=entry.session_id,
                at=entry.at,
                from_status=entry.from_status,
                to_status=entry.to_status,
                event=entry.event,
                source=entry.source,
            )
        )
        await self._db.flush()

    async def list_for_session(self, session_id: UUID) -> list[SubscriptionHistoryEntry]:
        result = await self._db.execute(
            select(SubscriptionHistoryRow)
            .where(SubscriptionHistoryRow.session_id == session_id)
            .order_by(SubscriptionHistoryRow.id)
        )
        return [
            SubscriptionHistoryEntry(
                r.session_id,
                r.at,
                cast(SubscriptionStatus, r.from_status),
                cast(SubscriptionStatus, r.to_status),
                r.event,
                r.source,
            )
            for r in result.scalars()
        ]
