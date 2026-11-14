"""End-to-end Stripe path: checkout, signed FakeStripe webhooks and gentle exit with a billing
failure. Real app and Postgres; the PaymentGateway is `FakePaymentGateway`, webhooks are signed
payloads verified by the real `StripeWebhookParser`."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.billing.errors import PaymentGatewayError
from tests.e2e.journey import answer_quiz_persona_b, ok
from tests.fakes.payments import FakePaymentGateway
from tests.fakes.stripe_webhooks import FakeStripe
from tests.presentation.test_exit_journey_api import _row_counts, _session_tables

stripe_fake = FakeStripe()
CUSTOMER = "cus_fake_1"
SUBSCRIPTION = "sub_fake_1"
# The checkout webhook starts a 28-day first period at app now (2026-01-05); each renewal invoice
# covers the next 28 days.
PERIOD_END = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


async def _send(hook: httpx.AsyncClient, event: tuple[bytes, str]) -> None:
    payload, signature = event
    r = await hook.post(
        "/api/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    assert r.status_code == 200, r.text


async def _subscription(client: httpx.AsyncClient) -> dict[str, Any]:
    body: dict[str, Any] = await ok(await client.get("/api/billing/subscription"))
    return body


async def _session_id(factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with factory() as db:
        value = await db.scalar(text("SELECT id FROM sessions"))
    assert isinstance(value, UUID)
    return value


async def _checkout_to_active(
    learner: httpx.AsyncClient,
    anonymous: httpx.AsyncClient,
    factory: async_sessionmaker[AsyncSession],
    gateway: FakePaymentGateway,
) -> UUID:
    await answer_quiz_persona_b(learner)
    assert (await learner.get("/api/lessons/m1_l1")).status_code == 402
    checkout = await ok(
        await learner.post("/api/billing/checkout", json={"autoRenewConsent": True})
    )
    assert checkout["checkoutId"] in gateway.sessions and checkout["url"]
    assert (await _subscription(learner))["status"] == "none"  # paid only once Stripe says so
    sid = await _session_id(factory)
    await _send(anonymous, stripe_fake.checkout_completed(sid, CUSTOMER, SUBSCRIPTION))
    sub = await _subscription(learner)
    assert sub["status"] == "active" and sub["source"] == "stripe" and sub["renewalCount"] == 0
    assert (await learner.get("/api/lessons/m1_l1")).status_code == 200
    return sid


async def test_stripe_path_journey_with_fake_webhooks(
    e2e_app: FastAPI,
    learner: httpx.AsyncClient,
    anonymous: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    gateway: FakePaymentGateway = e2e_app.state.payment_gateway
    await _checkout_to_active(learner, anonymous, session_factory, gateway)

    # renewal: invoice.paid for the next period
    await _send(anonymous, stripe_fake.invoice_paid(CUSTOMER, SUBSCRIPTION, PERIOD_END))
    sub = await _subscription(learner)
    assert sub["status"] == "active" and sub["renewalCount"] == 1
    assert sub["currentPeriodEnd"].startswith("2026-03-02")

    # failed payment: past_due, every gated route says 402 past_due, billing reads stay open
    await _send(anonymous, stripe_fake.invoice_payment_failed(CUSTOMER, SUBSCRIPTION, PERIOD_END))
    assert (await _subscription(learner))["status"] == "past_due"
    for path in ("/api/lessons/m1_l1", "/api/today", "/api/plan"):
        r = await learner.get(path)
        assert r.status_code == 402, path
        assert r.json()["error"]["details"] == {"reason": "past_due"}
    assert (await learner.get("/api/pricing")).status_code == 200

    # subscription deleted: canceled, the gate now says no_subscription
    deleted = stripe_fake.subscription_event(
        "customer.subscription.deleted", CUSTOMER, SUBSCRIPTION
    )
    await _send(anonymous, deleted)
    assert (await _subscription(learner))["status"] == "canceled"
    r = await learner.get("/api/lessons/m1_l1")
    assert r.status_code == 402
    assert r.json()["error"]["details"] == {"reason": "no_subscription"}
    async with session_factory() as db:
        history = (
            await db.execute(
                text("SELECT from_status, to_status, event FROM subscription_history ORDER BY id")
            )
        ).all()
    assert [(h[0], h[1]) for h in history] == [
        ("none", "active"),
        ("active", "active"),
        ("active", "past_due"),
        ("past_due", "canceled"),
    ]


async def test_gentle_exit_with_stripe_failure_returns_503_deletes_nothing_then_retry_succeeds(
    e2e_app: FastAPI,
    learner: httpx.AsyncClient,
    anonymous: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    gateway: FakePaymentGateway = e2e_app.state.payment_gateway
    sid = await _checkout_to_active(learner, anonymous, session_factory, gateway)
    tables = await _session_tables(session_factory)
    before = await _row_counts(session_factory, tables, sid)
    assert before["subscriptions"] == 1 and before["sessions"] == 1

    gateway.fail_with = PaymentGatewayError()
    r = await learner.post("/api/exit/gentle")
    assert r.status_code == 503, r.text
    assert r.json()["error"]["code"] == "billing_cancel_failed"
    assert await _row_counts(session_factory, tables, sid) == before  # nothing was deleted
    assert (await _subscription(learner))["status"] == "active"  # and the session still works

    gateway.fail_with = None
    r = await ok(await learner.post("/api/exit/gentle"))
    assert r["condolence"] and r["resources"]
    assert ("cancel_now", SUBSCRIPTION) in gateway.calls
    after = await _row_counts(session_factory, tables, sid)
    assert after == dict.fromkeys(after, 0), after
    assert (await learner.get("/api/billing/subscription")).status_code == 401
