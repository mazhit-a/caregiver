from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.billing.events import BillingEvent
from app.domain.billing.errors import InvalidWebhookSignature
from app.infrastructure.payments.webhook_parser import StripeWebhookParser
from tests.fakes.stripe_webhooks import TEST_WEBHOOK_SECRET, FakeStripe

PERIOD_END = datetime(2026, 2, 2, 9, 0, tzinfo=UTC)
parser = StripeWebhookParser(TEST_WEBHOOK_SECRET)
stripe_fake = FakeStripe()


def test_valid_signature_maps_checkout_completed() -> None:
    sid = uuid4()
    payload, sig = stripe_fake.checkout_completed(sid, "cus_1", "sub_1", event_id="evt_1")
    assert parser.parse(payload, sig) == BillingEvent(
        "evt_1",
        "checkout.session.completed",
        session_id=sid,
        customer_id="cus_1",
        subscription_id="sub_1",
        plan_id="four_week",
        paid=True,
    )


def test_unpaid_checkout_is_not_paid() -> None:
    payload, sig = stripe_fake.checkout_completed(uuid4(), "cus_1", "sub_1", paid=False)
    assert parser.parse(payload, sig).paid is False


def test_invoice_maps_reason_period_end_and_nested_metadata_session() -> None:
    sid = uuid4()
    payload, sig = stripe_fake.invoice_paid("cus_1", "sub_1", PERIOD_END, False, sid)
    event = parser.parse(payload, sig)
    assert (event.first_payment, event.period_end) == (False, PERIOD_END)
    assert (event.session_id, event.subscription_id) == (sid, "sub_1")
    payload, sig = stripe_fake.invoice_paid("cus_1", "sub_1", PERIOD_END, True)
    assert parser.parse(payload, sig).first_payment is True


def test_subscription_event_maps_cancel_flag() -> None:
    payload, sig = stripe_fake.subscription_event(
        "customer.subscription.updated", "cus_1", "sub_1", cancel_at_period_end=True
    )
    event = parser.parse(payload, sig)
    assert event.cancel_at_period_end and event.subscription_id == "sub_1"


def test_unknown_type_maps_to_bare_event() -> None:
    payload, sig = stripe_fake.event("charge.refunded", {"id": "ch_1"}, "evt_9")
    assert parser.parse(payload, sig) == BillingEvent("evt_9", "charge.refunded")


@pytest.mark.parametrize("case", ["wrong_secret", "tampered", "missing", "malformed", "old"])
def test_bad_signature_is_rejected(case: str) -> None:
    payload, sig = stripe_fake.checkout_completed(uuid4(), "cus_1", "sub_1")
    signature: str | None = sig
    if case == "wrong_secret":
        signature = stripe_fake.sign(payload, secret="whsec_other")
    elif case == "tampered":
        payload = payload.replace(b"cus_1", b"cus_2")
    elif case == "missing":
        signature = None
    elif case == "malformed":
        signature = "garbage"
    elif case == "old":
        signature = stripe_fake.sign(payload, at=1_000_000)
    with pytest.raises(InvalidWebhookSignature):
        parser.parse(payload, signature)


def test_empty_secret_rejects_even_a_signature_made_with_an_empty_secret() -> None:
    payload, _ = stripe_fake.checkout_completed(uuid4(), "cus_1", "sub_1")
    with pytest.raises(InvalidWebhookSignature):
        StripeWebhookParser("").parse(payload, stripe_fake.sign(payload, secret=""))
