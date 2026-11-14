"""Demo controls: read the app clock, simulate the next day, jump to the renewal, fail a payment."""

from datetime import timedelta

from app.application.demo.clock_sync import StripeClockSync
from app.application.demo.dto import DemoState
from app.application.ports import Clock, PaymentGateway, UnitOfWork
from app.domain.billing.entities import Subscription
from app.domain.billing.errors import (
    NoSubscriptionPeriod,
    NotAStripeSubscription,
    PaymentGatewayError,
)
from app.domain.session.entities import Session

_ONE_DAY = timedelta(hours=24)
_AFTER_RENEWAL = timedelta(hours=1)
_LIVE_STATUSES = ("demo", "active", "canceling", "past_due")


def _state(session: Session, subscription: Subscription, clock: Clock) -> DemoState:
    real_now = clock.now()
    return DemoState(
        app_now=session.app_now(real_now),
        app_today=session.app_today(real_now),
        clock_offset=session.clock_offset,
        subscription_status=subscription.status,
        current_period_end=subscription.current_period_end,
        renewal_count=subscription.renewal_count,
        billing_sync=subscription.billing_sync if subscription.source == "stripe" else "none",
    )


class GetDemoState:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session) -> DemoState:
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
        return _state(session, subscription, self._clock)


class AdvanceDemoDay:
    """`next-day`: the session's clock offset grows by 24 hours.

    A Stripe session's Test Clock is advanced to the new app time first (forward only); the offset
    is only saved when Stripe accepted it, and `billing_sync` is `pending` until
    `test_helpers.test_clock.ready` arrives.
    """

    def __init__(
        self, uow: UnitOfWork, clock: Clock, gateway: PaymentGateway | None = None
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._sync = StripeClockSync(uow, gateway)

    async def execute(self, session: Session) -> DemoState:
        new_offset = session.clock_offset + _ONE_DAY
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
        await self._sync.advance(subscription, self._clock.now() + new_offset)
        session.clock_offset = new_offset
        async with self._uow:
            await self._uow.sessions.save(session)
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            await self._uow.commit()
        return _state(session, subscription, self._clock)


class JumpToRenewal:
    """`jump-to-renewal`: offset so that `app_now` is one hour after the current period end.

    The demo renewal itself rolls lazily on the next request (see `RollDemoRenewals`); a Stripe
    session's Test Clock is advanced to the same time (forward only) and Stripe renews it.
    """

    def __init__(
        self, uow: UnitOfWork, clock: Clock, gateway: PaymentGateway | None = None
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._sync = StripeClockSync(uow, gateway)

    async def execute(self, session: Session) -> DemoState:
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
        period_end = subscription.current_period_end
        if period_end is None or subscription.status not in _LIVE_STATUSES:
            raise NoSubscriptionPeriod()
        await self._sync.advance(subscription, period_end + _AFTER_RENEWAL)
        async with self._uow:
            session.clock_offset = period_end + _AFTER_RENEWAL - self._clock.now()
            await self._uow.sessions.save(session)
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            await self._uow.commit()
        return _state(session, subscription, self._clock)


class FailNextPayment:
    """`fail-next-payment` (P1): the next renewal charge is declined (`past_due`).

    Only for a subscription made through Stripe checkout; the gateway attaches Stripe's failing
    test card as the default payment method (customer and subscription level).
    """

    def __init__(self, uow: UnitOfWork, clock: Clock, gateway: PaymentGateway | None) -> None:
        self._uow = uow
        self._clock = clock
        self._gateway = gateway

    async def execute(self, session: Session) -> DemoState:
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
        customer_id = subscription.stripe_customer_id
        if subscription.source != "stripe" or customer_id is None:
            raise NotAStripeSubscription()
        if self._gateway is None:
            raise PaymentGatewayError("Card payments are not configured on this server.")
        await self._gateway.attach_failing_payment_method(customer_id)
        return _state(session, subscription, self._clock)
