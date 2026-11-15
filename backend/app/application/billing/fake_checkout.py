"""The in-app fake Stripe checkout (`FAKE_STRIPE=true`): summary, pay and cancel.

A successful payment goes through the same `HandleStripeEvent` use case as a real
`checkout.session.completed` webhook, so the subscription, renewal date and everything downstream
behave exactly as with real Stripe. Nothing here changes a status directly.
"""

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from app.application.billing.checkout import CHECKOUT_ID_PLACEHOLDER
from app.application.billing.events import CHECKOUT_COMPLETED, BillingEvent
from app.application.billing.payments import FakeCheckoutRecord
from app.application.billing.stripe_events import HandleStripeEvent
from app.application.ports import Clock, ContentProvider, FakeCheckoutStore, UnitOfWork
from app.domain.billing.errors import CardError, CheckoutNotFound, FakeCheckoutClosed
from app.domain.billing.fake_cards import evaluate_test_card, last4
from app.domain.session.entities import Session


@dataclass(frozen=True)
class FakeCheckoutView:
    """What the simulated checkout page shows."""

    checkout_id: str
    status: str
    plan_id: str
    plan_label: str
    currency: str
    amount_today: Decimal
    intro_period_text: str
    renewal_price: Decimal
    renew_period_text: str
    first_renewal_date: date
    display_label: str | None
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class FakeCard:
    number: str
    exp_month: int
    exp_year: int
    cvc: str
    authenticated: bool = False  # the 3-D Secure "Authenticate" step was confirmed


PayStatus = Literal["paid", "requires_action"]


@dataclass(frozen=True)
class FakePayResult:
    status: PayStatus
    success_url: str


def _substitute(url: str, checkout_id: str) -> str:
    return url.replace(CHECKOUT_ID_PLACEHOLDER, checkout_id)


def _event_id(checkout_id: str) -> str:
    """Deterministic and not reversible: the checkout id is a secret and event ids are stored."""
    return "evt_fake_" + hashlib.sha256(checkout_id.encode()).hexdigest()[:24]


async def _load(
    uow: UnitOfWork, store: FakeCheckoutStore, checkout_id: str
) -> tuple[FakeCheckoutRecord, Session]:
    record = store.get(checkout_id)
    if record is None:
        raise CheckoutNotFound()
    async with uow:
        session = await uow.sessions.get(record.session_id)
    if session is None:
        raise CheckoutNotFound()
    return record, session


class GetFakeCheckout:
    """`GET /api/fake-stripe/checkout/{id}`."""

    def __init__(
        self, uow: UnitOfWork, content: ContentProvider, clock: Clock, store: FakeCheckoutStore
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._store = store

    async def execute(self, checkout_id: str) -> FakeCheckoutView:
        record, session = await _load(self._uow, self._store, checkout_id)
        pricing = self._content.pricing()
        plan = pricing.plan(record.plan_id)
        return FakeCheckoutView(
            checkout_id=record.id,
            status=record.status,
            plan_id=plan.id,
            plan_label=plan.label,
            currency=pricing.currency,
            amount_today=record.amount_today,
            intro_period_text=plan.intro_period_text,
            renewal_price=plan.renew_price,
            renew_period_text=plan.renew_period_text,
            first_renewal_date=plan.first_renewal_date(session.app_today(self._clock.now())),
            display_label=session.display_name,
            success_url=_substitute(record.success_url, record.id),
            cancel_url=record.cancel_url,
        )


class PayFakeCheckout:
    """`POST /api/fake-stripe/checkout/{id}/pay`.

    Evaluates the test card (domain). A refused card raises `CardError` and changes nothing. An
    accepted one marks the checkout paid and delivers a `checkout.session.completed` event to
    `HandleStripeEvent`. Paying an already paid checkout is a no-op that answers `paid` again.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        content: ContentProvider,
        clock: Clock,
        store: FakeCheckoutStore,
        handle_event: HandleStripeEvent,
    ) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock
        self._store = store
        self._handle = handle_event

    async def execute(self, checkout_id: str, card: FakeCard) -> FakePayResult:
        record, session = await _load(self._uow, self._store, checkout_id)
        success_url = _substitute(record.success_url, record.id)
        if record.status == "paid":
            return FakePayResult("paid", success_url)
        if record.status != "open":
            raise FakeCheckoutClosed(record.status)
        now = session.app_now(self._clock.now())
        outcome = evaluate_test_card(
            card.number,
            card.exp_month,
            card.exp_year,
            card.cvc,
            session.app_today(self._clock.now()),
        )
        self._store.note_attempt(record.id, last4(card.number), outcome.result)
        if outcome.result == "declined":
            raise CardError(outcome.code, outcome.decline_code, outcome.message)
        if outcome.result == "requires_action" and not card.authenticated:
            return FakePayResult("requires_action", success_url)
        plan = self._content.pricing().plan(record.plan_id)
        period_end: datetime = now + timedelta(days=plan.intro_days)
        paid = self._store.mark_paid(record.id, period_end, outcome.charge_fails_on_renewal)
        await self._handle.execute(
            BillingEvent(
                event_id=_event_id(record.id),
                type=CHECKOUT_COMPLETED,
                session_id=session.id,
                customer_id=record.customer_id,
                subscription_id=paid.subscription_id,
                plan_id=plan.id,
                paid=True,
                period_end=period_end,
            )
        )
        return FakePayResult("paid", success_url)


class CancelFakeCheckout:
    """`POST /api/fake-stripe/checkout/{id}/cancel`: the user backs out; nothing was charged."""

    def __init__(self, uow: UnitOfWork, store: FakeCheckoutStore) -> None:
        self._uow = uow
        self._store = store

    async def execute(self, checkout_id: str) -> str:
        record, _ = await _load(self._uow, self._store, checkout_id)
        if record.status == "paid":
            raise FakeCheckoutClosed(record.status)
        return self._store.mark_canceled(record.id).cancel_url
