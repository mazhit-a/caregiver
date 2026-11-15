"""In-app fake Stripe (`FAKE_STRIPE=true`): a `PaymentGateway` and a `FakeCheckoutStore` in memory.

For demos without Stripe keys. It never charges anything and never talks to the network.
State is in memory on purpose: checkouts are short-lived and the app runs one worker, so a restart
only forgets open checkouts (and the fake renewal schedule of earlier fake subscriptions).

Like Stripe, it only receives what `CheckoutRequest` carries (plan id, amount, internal session
UUID). Checkout ids are bearer secrets (`cs_fake_...`, from the `TokenGenerator`) and are redacted
in logs by `infrastructure/logging.py`.

Clock advances emulate Stripe's Test Clock: due renewals are delivered as `invoice.paid` (or
`invoice.payment_failed` when the card was the "first charge fails" test card or the demo control
"fail next payment" was used), followed by `test_helpers.test_clock.ready`, all through the same
event sink a real webhook feeds (`HandleStripeEvent`).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID

from app.application.billing.events import (
    INVOICE_PAID,
    INVOICE_PAYMENT_FAILED,
    SUBSCRIPTION_DELETED,
    TEST_CLOCK_READY,
    BillingEvent,
)
from app.application.billing.payments import (
    CheckoutRequest,
    CheckoutSessionInfo,
    CheckoutSessionRef,
    CustomerRef,
    FakeCheckoutRecord,
)
from app.application.ports import TokenGenerator
from app.domain.billing.errors import CheckoutNotFound, PaymentGatewayError

EventSink = Callable[[BillingEvent], Awaitable[object]]
RenewDays = Callable[[str], int]


@dataclass
class _FakeSubscription:
    session_id: UUID
    plan_id: str
    customer_id: str
    subscription_id: str
    period_end: datetime
    charge_fails: bool
    cancel_at_period_end: bool = False


class FakeStripeGateway:
    def __init__(
        self,
        tokens: TokenGenerator,
        public_app_url: str,
        renew_days: RenewDays,
        sink: EventSink | None = None,
    ) -> None:
        self._tokens = tokens
        self._base_url = public_app_url.rstrip("/")
        self._renew_days = renew_days
        self._sink = sink
        self._checkouts: dict[str, FakeCheckoutRecord] = {}
        self._clocks: dict[str, str] = {}  # test clock id -> customer id
        self._subscriptions: dict[str, _FakeSubscription] = {}  # customer id -> subscription

    def bind_sink(self, sink: EventSink) -> None:
        """Where simulated provider events go (the composition root wires `HandleStripeEvent`)."""
        self._sink = sink

    # --- PaymentGateway ------------------------------------------------------------------------

    async def create_customer(self, session_id: UUID, clock_frozen_at: datetime) -> CustomerRef:
        suffix = self._tokens.new_token()[:12]
        customer = CustomerRef(
            customer_id=f"cus_fake_{suffix}", test_clock_id=f"clock_fake_{suffix}"
        )
        self._clocks[customer.test_clock_id] = customer.customer_id
        return customer

    async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutSessionRef:
        checkout_id = f"cs_fake_{self._tokens.new_token()}"
        self._checkouts[checkout_id] = FakeCheckoutRecord(
            id=checkout_id,
            session_id=request.session_id,
            plan_id=request.plan_id,
            amount_today=request.amount_today,
            customer_id=request.customer_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutSessionRef(
            id=checkout_id, url=f"{self._base_url}/fake-checkout/{checkout_id}"
        )

    async def retrieve_checkout_session(self, checkout_id: str) -> CheckoutSessionInfo:
        record = self._checkouts.get(checkout_id)
        if record is None:
            raise CheckoutNotFound()
        return CheckoutSessionInfo(
            id=record.id,
            session_id=record.session_id,
            plan_id=record.plan_id,
            paid=record.status == "paid",
            customer_id=record.customer_id,
            subscription_id=record.subscription_id,
            period_end=record.period_end,
        )

    async def cancel_at_period_end(self, subscription_id: str) -> None:
        for sub in self._subscriptions.values():
            if sub.subscription_id == subscription_id:
                sub.cancel_at_period_end = True

    async def cancel_now(self, subscription_id: str) -> None:
        for customer_id, sub in list(self._subscriptions.items()):
            if sub.subscription_id == subscription_id:
                del self._subscriptions[customer_id]

    async def advance_test_clock(self, test_clock_id: str, to: datetime) -> None:
        customer_id = self._clocks.get(test_clock_id)
        sub = self._subscriptions.get(customer_id) if customer_id else None
        while sub is not None and sub.period_end <= to:
            if sub.cancel_at_period_end:
                await self._emit(sub, SUBSCRIPTION_DELETED)
                del self._subscriptions[sub.customer_id]
                break
            sub.period_end += timedelta(days=self._renew_days(sub.plan_id))
            if sub.charge_fails:
                await self._emit(sub, INVOICE_PAYMENT_FAILED)
                break  # Stripe retries later; the demo stops at the failure
            await self._emit(sub, INVOICE_PAID)
        if self._sink is not None:
            await self._sink(
                BillingEvent(
                    event_id=f"evt_fake_{self._tokens.new_token()[:20]}",
                    type=TEST_CLOCK_READY,
                    test_clock_id=test_clock_id,
                )
            )

    async def attach_failing_payment_method(self, customer_id: str) -> None:
        sub = self._subscriptions.get(customer_id)
        if sub is None:
            raise PaymentGatewayError("There is no simulated subscription for this customer.")
        sub.charge_fails = True

    async def _emit(self, sub: _FakeSubscription, event_type: str) -> None:
        if self._sink is None:
            return
        await self._sink(
            BillingEvent(
                event_id=f"evt_fake_{self._tokens.new_token()[:20]}",
                type=event_type,
                session_id=sub.session_id,
                customer_id=sub.customer_id,
                subscription_id=sub.subscription_id,
                plan_id=sub.plan_id,
                period_end=sub.period_end,
            )
        )

    # --- FakeCheckoutStore ---------------------------------------------------------------------

    def get(self, checkout_id: str) -> FakeCheckoutRecord | None:
        return self._checkouts.get(checkout_id)

    def note_attempt(self, checkout_id: str, last4: str, outcome: str) -> None:
        record = self._require(checkout_id)
        self._checkouts[checkout_id] = replace(record, last4=last4, last_outcome=outcome)

    def mark_paid(
        self, checkout_id: str, period_end: datetime, charge_fails_on_renewal: bool
    ) -> FakeCheckoutRecord:
        record = self._require(checkout_id)
        subscription_id = f"sub_fake_{self._tokens.new_token()[:16]}"
        paid = replace(
            record, status="paid", subscription_id=subscription_id, period_end=period_end
        )
        self._checkouts[checkout_id] = paid
        self._subscriptions[record.customer_id] = _FakeSubscription(
            session_id=record.session_id,
            plan_id=record.plan_id,
            customer_id=record.customer_id,
            subscription_id=subscription_id,
            period_end=period_end,
            charge_fails=charge_fails_on_renewal,
        )
        return paid

    def mark_canceled(self, checkout_id: str) -> FakeCheckoutRecord:
        record = self._require(checkout_id)
        canceled = replace(record, status="canceled")
        self._checkouts[checkout_id] = canceled
        return canceled

    def _require(self, checkout_id: str) -> FakeCheckoutRecord:
        record = self._checkouts.get(checkout_id)
        if record is None:
            raise CheckoutNotFound()
        return record
