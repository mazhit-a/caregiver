from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.billing.payments import CheckoutRequest
from app.domain.billing.errors import PaymentGatewayError
from app.infrastructure.payments.stripe_gateway import StripePaymentGateway
from tests.fakes.payments import RecordingStripeHttpClient, stripe_client_with

FROZEN = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def _gateway() -> tuple[StripePaymentGateway, RecordingStripeHttpClient]:
    http = RecordingStripeHttpClient()
    return StripePaymentGateway(stripe_client_with(http)), http


async def test_customer_is_created_on_a_test_clock_frozen_at_the_given_time() -> None:
    gateway, http = _gateway()
    sid = uuid4()
    ref = await gateway.create_customer(sid, FROZEN)
    assert (ref.customer_id, ref.test_clock_id) == ("cus_1", "clock_1")
    assert http.fields("/v1/test_helpers/test_clocks") == {
        "frozen_time": str(int(FROZEN.timestamp()))
    }
    assert http.fields("/v1/customers") == {
        "test_clock": "clock_1",
        "metadata[session_id]": str(sid),
    }


async def test_checkout_session_payload_has_only_session_uuid_plan_amount_price_and_coupon() -> (
    None
):
    gateway, http = _gateway()
    sid = uuid4()
    ref = await gateway.create_checkout_session(
        CheckoutRequest(
            customer_id="cus_1",
            session_id=sid,
            plan_id="four_week",
            price_id="price_renew",
            coupon_id="coupon_intro",
            amount_today=Decimal("14.99"),
            success_url="https://app.example/ok?c={CHECKOUT_SESSION_ID}",
            cancel_url="https://app.example/no",
        )
    )
    assert ref.id == "cs_test_1" and ref.url == "https://pay.test/cs"
    assert http.fields("/v1/checkout/sessions") == {
        "mode": "subscription",
        "customer": "cus_1",
        "line_items[0][price]": "price_renew",
        "line_items[0][quantity]": "1",
        "discounts[0][coupon]": "coupon_intro",
        "success_url": "https://app.example/ok?c={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://app.example/no",
        "metadata[session_id]": str(sid),
        "metadata[plan_id]": "four_week",
        "metadata[amount]": "14.99",
        "subscription_data[metadata][session_id]": str(sid),
        "subscription_data[metadata][plan_id]": "four_week",
    }


async def test_retrieve_paid_session_maps_fields_and_period_end_from_item() -> None:
    gateway, http = _gateway()
    sid = uuid4()
    http.checkout_session = {
        "status": "complete",
        "payment_status": "paid",
        "metadata": {"session_id": str(sid), "plan_id": "four_week"},
        "customer": "cus_1",
        "subscription": {
            "id": "sub_1",
            "object": "subscription",
            "items": {"object": "list", "data": [{"id": "si_1", "current_period_end": 1770000000}]},
        },
    }
    info = await gateway.retrieve_checkout_session("cs_test_9")
    assert info.paid and info.session_id == sid and info.plan_id == "four_week"
    assert (info.customer_id, info.subscription_id) == ("cus_1", "sub_1")
    assert info.period_end == datetime.fromtimestamp(1770000000, UTC)


async def test_retrieve_open_session_is_unpaid_and_foreign_metadata_is_ignored() -> None:
    gateway, http = _gateway()
    http.checkout_session = {"status": "open", "payment_status": "unpaid", "metadata": {}}
    info = await gateway.retrieve_checkout_session("cs_test_9")
    assert not info.paid and info.session_id is None and info.subscription_id is None


async def test_remaining_operations_send_the_expected_requests() -> None:
    gateway, http = _gateway()
    await gateway.cancel_at_period_end("sub_1")
    await gateway.cancel_now("sub_1")
    await gateway.advance_test_clock("clock_1", FROZEN)
    await gateway.attach_failing_payment_method("cus_1")
    assert ("POST", "/v1/subscriptions/sub_1", {"cancel_at_period_end": "true"}) in http.requests
    assert ("DELETE", "/v1/subscriptions/sub_1", {}) in http.requests
    assert http.fields("/v1/test_helpers/test_clocks/clock_1/advance") == {
        "frozen_time": str(int(FROZEN.timestamp()))
    }
    assert http.fields("/v1/payment_methods/pm_card_chargeCustomerFail/attach") == {
        "customer": "cus_1"
    }
    assert http.fields("/v1/customers/cus_1") == {
        "invoice_settings[default_payment_method]": "pm_1"
    }
    # a subscription-level default payment method would override the customer's: set it too
    assert http.fields("/v1/subscriptions/sub_9") == {"default_payment_method": "pm_1"}


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (400, {"error": {"type": "invalid_request_error", "message": "No such coupon"}}),
        (401, {"error": {"type": "invalid_request_error", "message": "Invalid API Key"}}),
        (402, {"error": {"type": "card_error", "message": "declined", "code": "card_declined"}}),
        (429, {"error": {"type": "rate_limit_error", "message": "slow down"}}),
        (500, {"error": {"type": "api_error", "message": "boom"}}),
    ],
)
async def test_stripe_sdk_errors_become_PaymentGatewayError(
    status: int, body: dict[str, object]
) -> None:
    gateway, http = _gateway()
    http.error = (status, body)
    with pytest.raises(PaymentGatewayError) as raised:
        await gateway.retrieve_checkout_session("cs_test_9")
    assert raised.value.details["hint"] == "demo_mode"
    assert "No such coupon" not in raised.value.message  # provider text is not passed on
