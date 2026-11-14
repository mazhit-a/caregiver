"""Keep a Stripe Test Clock in step with the session's app clock (demo controls only)."""

from datetime import datetime
from uuid import UUID

from app.application.ports import PaymentGateway, UnitOfWork
from app.domain.billing.entities import BillingSync, Subscription
from app.domain.billing.errors import PaymentGatewayError


class StripeClockSync:
    """Advance the Stripe Test Clock to an app time, forward only.

    Order: store `billing_sync = pending` and the new clock time first (so a fast
    `test_clock.ready` webhook finds `pending` and sets `done`), then call Stripe. When Stripe
    fails the previous values are restored and the error is raised, so nothing changes.
    """

    def __init__(self, uow: UnitOfWork, gateway: PaymentGateway | None) -> None:
        self._uow = uow
        self._gateway = gateway

    async def advance(self, subscription: Subscription, target: datetime) -> bool:
        """True when the clock was advanced (billing_sync is now pending); False when the
        session has no Stripe Test Clock or `target` is not after the clock's current time."""
        if not subscription.clock_needs_advance(target):
            return False
        clock_id = subscription.stripe_test_clock_id
        previous_at, previous_sync = subscription.stripe_clock_at, subscription.billing_sync
        if self._gateway is None or clock_id is None:
            raise PaymentGatewayError("Card payments are not configured on this server.")
        subscription.clock_advanced(target)
        async with self._uow:
            await self._uow.subscriptions.save(subscription)
            await self._uow.commit()
        try:
            await self._gateway.advance_test_clock(clock_id, target)
        except PaymentGatewayError:
            await self._restore(subscription.session_id, previous_at, previous_sync)
            raise
        return True

    async def _restore(self, session_id: UUID, at: datetime | None, sync: BillingSync) -> None:
        async with self._uow:
            current = await self._uow.subscriptions.get(session_id)
            if current is not None:
                current.stripe_clock_at = at
                current.billing_sync = sync
                await self._uow.subscriptions.save(current)
            await self._uow.commit()
