"""Provider-neutral billing events: what a verified webhook means for us. No Stripe types."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# Provider event types the application handles (the registry lives in `HandleStripeEvent`).
CHECKOUT_COMPLETED = "checkout.session.completed"
INVOICE_PAID = "invoice.paid"
INVOICE_PAYMENT_FAILED = "invoice.payment_failed"
SUBSCRIPTION_UPDATED = "customer.subscription.updated"
SUBSCRIPTION_DELETED = "customer.subscription.deleted"
TEST_CLOCK_READY = "test_helpers.test_clock.ready"


@dataclass(frozen=True)
class BillingEvent:
    """One verified webhook event, reduced to the fields the handlers use.

    `session_id` is the internal session UUID from the metadata we set at checkout (None when the
    event carries none); `customer_id` is the fallback for finding the session.
    """

    event_id: str
    type: str
    session_id: UUID | None = None
    customer_id: str | None = None
    subscription_id: str | None = None
    plan_id: str | None = None
    paid: bool = False  # checkout.session.completed: the payment went through
    first_payment: bool = False  # invoice.paid: the invoice that started the subscription
    period_end: datetime | None = None  # invoice.paid: end of the period that was just paid
    cancel_at_period_end: bool = False  # customer.subscription.updated
