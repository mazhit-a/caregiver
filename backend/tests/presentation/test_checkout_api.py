import httpx
import pytest
from fastapi import FastAPI

from app.domain.billing.errors import PaymentGatewayError
from tests.fakes.payments import FakePaymentGateway
from tests.presentation import test_billing_api as billing_tests

content = billing_tests.content  # fixtures shared with the billing API tests
pclient = billing_tests.pclient
_answer_and_complete = billing_tests._answer_and_complete


@pytest.fixture
def gateway(db_app: FastAPI) -> FakePaymentGateway:
    fake = FakePaymentGateway()
    db_app.state.payment_gateway = fake
    return fake


async def test_checkout_requires_consent_422(
    pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    await _answer_and_complete(pclient)
    r = await pclient.post("/api/billing/checkout", json={"autoRenewConsent": False})
    assert r.status_code == 422 and r.json()["error"]["code"] == "consent_required"
    r = await pclient.post("/api/billing/checkout", json={})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert gateway.customers == [] and gateway.checkout_requests == []
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "none"


async def test_checkout_returns_url_and_stores_consent_without_changing_status(
    pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    await _answer_and_complete(pclient)
    r = await pclient.post("/api/billing/checkout", json={"autoRenewConsent": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("https://checkout.stripe.test/") and body["checkoutId"]
    sub = (await pclient.get("/api/billing/subscription")).json()
    assert sub["status"] == "none" and sub["autoRenewConsentAt"] is not None
    [request] = gateway.checkout_requests
    assert request.success_url == (
        "http://localhost:3000/checkout/return?checkout_id={CHECKOUT_SESSION_ID}"
    )


async def test_checkout_when_already_subscribed_409(
    pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    await _answer_and_complete(pclient)
    assert (
        await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    ).status_code == 200
    r = await pclient.post("/api/billing/checkout", json={"autoRenewConsent": True})
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_subscribed"
    assert gateway.customers == []


async def test_stripe_sdk_errors_become_PaymentGatewayError_and_api_returns_502_shape_with_demo_mode_hint(  # noqa: E501
    pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    await _answer_and_complete(pclient)
    gateway.fail_with = PaymentGatewayError()
    for r in (
        await pclient.post("/api/billing/checkout", json={"autoRenewConsent": True}),
        await pclient.get("/api/billing/checkout/cs_test_any"),
    ):
        assert r.status_code == 502, r.text
        error = r.json()["error"]
        assert error["code"] == "payment_gateway_error"
        assert error["details"]["hint"] == "demo_mode"
        assert error["details"]["demoEndpoint"] == "/api/billing/demo"


async def test_without_stripe_key_checkout_is_502_with_hint_and_demo_still_works(
    pclient: httpx.AsyncClient,
) -> None:
    await _answer_and_complete(pclient)  # the default test app has no usable Stripe key
    r = await pclient.post("/api/billing/checkout", json={"autoRenewConsent": True})
    assert r.status_code == 502 and r.json()["error"]["details"]["hint"] == "demo_mode"
    r = await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 200 and r.json()["status"] == "demo"


async def test_reconcile_over_http_paid_unpaid_and_foreign(
    pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    await _answer_and_complete(pclient)
    checkout_id = (
        await pclient.post("/api/billing/checkout", json={"autoRenewConsent": True})
    ).json()["checkoutId"]
    unpaid = await pclient.get(f"/api/billing/checkout/{checkout_id}")
    assert unpaid.status_code == 200
    assert unpaid.json()["paid"] is False and unpaid.json()["message"]
    assert unpaid.json()["subscription"]["status"] == "none"

    gateway.pay(checkout_id)
    paid = await pclient.get(f"/api/billing/checkout/{checkout_id}")
    assert paid.json()["paid"] is True and paid.json()["message"] is None
    assert paid.json()["subscription"]["status"] == "active"
    assert paid.json()["subscription"]["source"] == "stripe"
    again = await pclient.get(f"/api/billing/checkout/{checkout_id}")
    assert again.json()["subscription"]["renewalCount"] == 0

    other = await pclient.post("/api/session")  # a different session asks for the same checkout
    r = await pclient.get(
        f"/api/billing/checkout/{checkout_id}", headers={"X-Session-Token": other.json()["token"]}
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "checkout_not_found"
