"""`HandleStripeEvent`: processes one verified webhook event exactly once."""

from collections.abc import Awaitable, Callable

from app.application.billing.checkout import stripe_start_request
from app.application.billing.events import (
    CHECKOUT_COMPLETED,
    INVOICE_PAID,
    INVOICE_PAYMENT_FAILED,
    SUBSCRIPTION_DELETED,
    SUBSCRIPTION_UPDATED,
    TEST_CLOCK_READY,
    BillingEvent,
)
from app.application.billing.use_cases import StartSubscription
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.billing.entities import Subscription
from app.domain.session.entities import Session

SOURCE = "stripe"

Handler = Callable[[BillingEvent], Awaitable[None]]


class HandleStripeEvent:
    """Records the event id first, then dispatches by type through the registry.

    - A duplicate delivery (already processed) does nothing. An event recorded but never finished
      (the handler failed, Stripe retries) is handled again.
    - Unknown event types and events whose session cannot be found are recorded and acknowledged.
    - Status changes go through the `Subscription` entity, at app time, with source `stripe`.
      A change the current status does not allow (late or out-of-order event) is skipped.
    """

    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._start = StartSubscription(uow, content, clock)
        # {event_type: handler}. Later increments add their event types here.
        self.registry: dict[str, Handler] = {
            CHECKOUT_COMPLETED: self._checkout_completed,
            INVOICE_PAID: self._invoice_paid,
            INVOICE_PAYMENT_FAILED: self._invoice_payment_failed,
            SUBSCRIPTION_UPDATED: self._subscription_updated,
            SUBSCRIPTION_DELETED: self._subscription_deleted,
            TEST_CLOCK_READY: self._test_clock_ready,
        }

    async def execute(self, event: BillingEvent) -> bool:
        """True when the event was handled now, False for a processed duplicate."""
        async with self._uow:
            should_process = await self._uow.stripe_events.begin(
                event.event_id, event.type, self._clock.now()
            )
            await self._uow.commit()
        if not should_process:
            return False
        handler = self.registry.get(event.type)
        if handler is not None:
            await handler(event)
        async with self._uow:
            await self._uow.stripe_events.mark_processed(event.event_id, self._clock.now())
            await self._uow.commit()
        return True

    # --- helpers -------------------------------------------------------------------------------

    async def _resolve_session(self, event: BillingEvent) -> Session | None:
        """The internal session: metadata session id first, then the stored customer id."""
        async with self._uow:
            if event.session_id is not None:
                found = await self._uow.sessions.get(event.session_id)
                if found is not None:
                    return found
            if event.customer_id is not None:
                subscription = await self._uow.subscriptions.get_by_stripe_customer_id(
                    event.customer_id
                )
                if subscription is not None:
                    return await self._uow.sessions.get(subscription.session_id)
        return None

    async def _change(
        self, event: BillingEvent, apply: Callable[[Subscription, Session], bool]
    ) -> None:
        """Load the subscription, let `apply` change it (True = changed), persist with history."""
        session = await self._resolve_session(event)
        if session is None:
            return
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id)
            if subscription is None or subscription.source != SOURCE:
                return
            if not apply(subscription, session):
                return
            await self._uow.subscriptions.save(subscription)
            for entry in subscription.pull_history():
                await self._uow.subscription_history.add(entry)
            await self._uow.commit()

    # --- handlers ------------------------------------------------------------------------------

    async def _checkout_completed(self, event: BillingEvent) -> None:
        if not event.paid:
            return
        session = await self._resolve_session(event)
        if session is None:
            return
        request = stripe_start_request(
            self._content,
            session.app_now(self._clock.now()),
            event.plan_id,
            event.period_end,
            event.customer_id,
            event.subscription_id,
        )
        await self._start.execute(session, request)  # idempotent with the reconcile

    async def _invoice_paid(self, event: BillingEvent) -> None:
        # The first invoice is the subscription start (checkout.session.completed / reconcile);
        # every later paid invoice is a renewal, or the recovery of a past-due payment.
        if event.first_payment or event.period_end is None:
            return
        period_end = event.period_end

        def apply(subscription: Subscription, session: Session) -> bool:
            if subscription.status not in ("active", "past_due"):
                return False
            current_end = subscription.current_period_end
            if subscription.status == "active" and current_end and period_end <= current_end:
                return False  # this period is already counted
            subscription.renew(session.app_now(self._clock.now()), period_end, "renewed", SOURCE)
            return True

        await self._change(event, apply)

    async def _invoice_payment_failed(self, event: BillingEvent) -> None:
        def apply(subscription: Subscription, session: Session) -> bool:
            if subscription.status != "active":
                return False
            subscription.mark_past_due(session.app_now(self._clock.now()), SOURCE)
            return True

        await self._change(event, apply)

    async def _subscription_updated(self, event: BillingEvent) -> None:
        def apply(subscription: Subscription, session: Session) -> bool:
            if not event.cancel_at_period_end or subscription.status != "active":
                return False
            subscription.cancel_at_period_end(session.app_now(self._clock.now()), SOURCE)
            return True

        await self._change(event, apply)

    async def _subscription_deleted(self, event: BillingEvent) -> None:
        def apply(subscription: Subscription, session: Session) -> bool:
            if subscription.status not in ("active", "past_due", "canceling"):
                return False
            subscription.cancel_now(session.app_now(self._clock.now()), SOURCE)
            return True

        await self._change(event, apply)

    async def _test_clock_ready(self, event: BillingEvent) -> None:
        """The event carries only the clock id: find the subscription through the stored id and
        set `billing_sync` to done. Unknown clocks, and clocks with nothing pending, are ignored."""
        if event.test_clock_id is None:
            return
        async with self._uow:
            subscription = await self._uow.subscriptions.get_by_stripe_test_clock_id(
                event.test_clock_id
            )
            if subscription is None or not subscription.clock_ready():
                return
            await self._uow.subscriptions.save(subscription)
            await self._uow.commit()
