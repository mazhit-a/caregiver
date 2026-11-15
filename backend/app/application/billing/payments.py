"""DTOs of the payment gateway port. Provider types never appear here."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CustomerRef:
    customer_id: str
    test_clock_id: str


@dataclass(frozen=True)
class CheckoutRequest:
    """Everything the provider may receive about a checkout: ids, price, coupon, amount, urls.

    No email, name or quiz value ever goes here.
    """

    customer_id: str
    session_id: UUID  # the internal session UUID (the only identifier Stripe gets)
    plan_id: str
    price_id: str  # the plan's renewal price
    coupon_id: str  # the one-time intro coupon
    amount_today: Decimal
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class CheckoutSessionRef:
    id: str
    url: str


@dataclass(frozen=True)
class CheckoutSessionInfo:
    """A checkout session as fetched back from the provider (for the return-page reconcile)."""

    id: str
    session_id: UUID | None  # from the metadata we set; None when absent or malformed
    plan_id: str | None
    paid: bool  # the session is complete and the payment went through
    customer_id: str | None
    subscription_id: str | None
    period_end: datetime | None  # end of the first subscription period, in provider time


@dataclass(frozen=True)
class FakeCheckoutRecord:
    """A simulated checkout as the fake store holds it. Only the last four digits of the card are
    kept (never the number, expiry or CVC)."""

    id: str
    session_id: UUID
    plan_id: str
    amount_today: Decimal
    customer_id: str
    success_url: str  # still holds Stripe's {CHECKOUT_SESSION_ID} placeholder
    cancel_url: str
    status: str = "open"  # open | paid | canceled
    last4: str | None = None
    last_outcome: str | None = None  # succeeds | requires_action | declined
    subscription_id: str | None = None
    period_end: datetime | None = None
