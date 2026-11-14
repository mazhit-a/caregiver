"""Stripe checkout: create the Checkout Session, and reconcile it on the return page."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.billing.dto import StartRequest
from app.application.billing.payments import CheckoutRequest, CheckoutSessionRef
from app.application.billing.use_cases import StartSubscription
from app.application.ports import Clock, ContentProvider, PaymentGateway, UnitOfWork
from app.domain.billing.entities import STARTED_STATUSES, Subscription
from app.domain.billing.errors import AlreadySubscribed, CheckoutNotFound, ConsentRequired
from app.domain.plan.errors import NoPlan
from app.domain.session.entities import Session

# Stripe replaces this literal placeholder with the real Checkout Session id.
_CHECKOUT_ID_PLACEHOLDER = "{CHECKOUT_SESSION_ID}"


class CreateCheckout:
    """`POST /api/billing/checkout`.

    Order matters: the auto-renew consent is stored and committed before anything is sent to
    Stripe, then the Stripe customer (on a Test Clock frozen at app time) is created once and its
    id stored, then the Checkout Session is created with the plan's renewal price plus the intro
    coupon. Stripe only ever receives the plan id, the amount and the internal session UUID.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        content: ContentProvider,
        clock: Clock,
        gateway: PaymentGateway,
        public_app_url: str,
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._gateway = gateway
        self._base_url = public_app_url.rstrip("/")

    async def execute(
        self, session: Session, auto_renew_consent: bool, plan_id: str | None
    ) -> CheckoutSessionRef:
        if not auto_renew_consent:
            raise ConsentRequired()
        plan = self._content.pricing().plan(plan_id)
        now = session.app_now(self._clock.now())
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            if subscription.status in STARTED_STATUSES:
                raise AlreadySubscribed()
            if await self._uow.plans.get(session.id) is None:
                raise NoPlan()
            subscription.record_consent(now)
            await self._uow.subscriptions.save(subscription)  # consent before any Stripe call
            await self._uow.commit()
        customer_id = subscription.stripe_customer_id
        if customer_id is None:
            customer = await self._gateway.create_customer(session.id, now)
            customer_id = customer.customer_id
            async with self._uow:
                subscription.stripe_customer_id = customer_id
                subscription.stripe_test_clock_id = customer.test_clock_id
                subscription.stripe_clock_at = now  # the clock was created frozen at app time
                await self._uow.subscriptions.save(subscription)
                await self._uow.commit()
        return await self._gateway.create_checkout_session(
            CheckoutRequest(
                customer_id=customer_id,
                session_id=session.id,
                plan_id=plan.id,
                price_id=plan.stripe_renew_price_id,
                coupon_id=plan.stripe_intro_coupon_id,
                amount_today=plan.intro_price,
                success_url=f"{self._base_url}/checkout/return?checkout_id={_CHECKOUT_ID_PLACEHOLDER}",
                cancel_url=f"{self._base_url}/paywall?checkout=canceled",
            )
        )


def stripe_start_request(
    content: ContentProvider,
    now: datetime,
    plan_id: str | None,
    period_end: datetime | None,
    customer_id: str | None,
    subscription_id: str | None,
) -> StartRequest:
    """The one `StartRequest` of a paid Stripe checkout: used by the return-page reconcile and by
    the `checkout.session.completed` webhook, so both starts are identical (and idempotent)."""
    plan = content.pricing().plan(plan_id)
    return StartRequest(
        "stripe",
        auto_renew_consent=False,  # stored by CreateCheckout
        plan_id=plan.id,
        period_end=period_end or now + timedelta(days=plan.intro_days),
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
    )


@dataclass(frozen=True)
class ReconcileResult:
    paid: bool
    subscription: Subscription


class ReconcileCheckout:
    """`GET /api/billing/checkout/{id}`: fetch the Checkout Session and start the subscription.

    Uses the same idempotent `StartSubscription` as the webhook, so reconcile and webhook may
    arrive in any order and any number of times. An unpaid session changes nothing.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        content: ContentProvider,
        clock: Clock,
        gateway: PaymentGateway,
        start: StartSubscription,
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._gateway = gateway
        self._start = start

    async def execute(self, session: Session, checkout_id: str) -> ReconcileResult:
        info = await self._gateway.retrieve_checkout_session(checkout_id)
        if info.session_id != session.id:
            raise CheckoutNotFound()
        if not info.paid:
            async with self._uow:
                current = await self._uow.subscriptions.get(session.id)
            return ReconcileResult(False, current or Subscription(session.id))
        request = stripe_start_request(
            self._content,
            session.app_now(self._clock.now()),
            info.plan_id,
            info.period_end,
            info.customer_id,
            info.subscription_id,
        )
        subscription = await self._start.execute(session, request)
        return ReconcileResult(True, subscription)
