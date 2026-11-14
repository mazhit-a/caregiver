from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.payments.webhook_parser import StripeWebhookParser
from tests.fakes.payments import FakePaymentGateway
from tests.fakes.stripe_webhooks import TEST_WEBHOOK_SECRET, FakeStripe
from tests.presentation import test_billing_api as billing_tests

content = billing_tests.content  # fixtures shared with the billing API tests
pclient = billing_tests.pclient
_answer_and_complete = billing_tests._answer_and_complete
_session_id = billing_tests._session_id

stripe_fake = FakeStripe()
# The webhook start ends the first period at app now (2026-01-05) + intro days (28); every
# renewal invoice covers the next period, so its period end lies after the current one.
PERIOD_END = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)
CUSTOMER = "cus_fake_1"
SUBSCRIPTION = "sub_fake_1"


@pytest.fixture
def gateway(db_app: FastAPI) -> FakePaymentGateway:
    fake = FakePaymentGateway()
    db_app.state.payment_gateway = fake
    db_app.state.webhook_parser = StripeWebhookParser(TEST_WEBHOOK_SECRET)
    return fake


@pytest.fixture
async def hook(db_app: FastAPI, content: object) -> AsyncIterator[httpx.AsyncClient]:
    """A client without a session token: webhooks authenticate by signature only."""
    transport = httpx.ASGITransport(app=db_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _send(
    hook: httpx.AsyncClient, event: tuple[bytes, str], signature: str | None = None
) -> httpx.Response:
    payload, sig = event
    headers = {"Stripe-Signature": signature or sig, "Content-Type": "application/json"}
    return await hook.post("/api/webhooks/stripe", content=payload, headers=headers)


async def _checkout(pclient: httpx.AsyncClient) -> str:
    """Quiz done, consent stored, Stripe customer created; returns the checkout id."""
    await _answer_and_complete(pclient)
    r = await pclient.post("/api/billing/checkout", json={"autoRenewConsent": True})
    assert r.status_code == 200, r.text
    return str(r.json()["checkoutId"])


async def _start_via_webhook(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    factory: async_sessionmaker[AsyncSession],
) -> UUID:
    await _checkout(pclient)
    sid = await _session_id(factory)
    r = await _send(hook, stripe_fake.checkout_completed(sid, CUSTOMER, SUBSCRIPTION))
    assert r.status_code == 200, r.text
    return sid


async def _rows(factory: async_sessionmaker[AsyncSession], sql: str) -> list[tuple[Any, ...]]:
    async with factory() as db:
        return [tuple(r) for r in (await db.execute(text(sql))).all()]


async def _status(pclient: httpx.AsyncClient) -> dict[str, Any]:
    body: dict[str, Any] = (await pclient.get("/api/billing/subscription")).json()
    return body


async def test_wrong_signature_returns_400_and_changes_nothing(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _checkout(pclient)
    sid = await _session_id(session_factory)
    event = stripe_fake.checkout_completed(sid, CUSTOMER, SUBSCRIPTION)
    r = await _send(hook, event, signature=stripe_fake.sign(event[0], secret="whsec_wrong"))
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_webhook_signature"
    assert (await _status(pclient))["status"] == "none"
    assert await _rows(session_factory, "SELECT * FROM stripe_events") == []


async def test_missing_signature_header_400(
    hook: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    payload, _ = stripe_fake.test_clock_ready()
    r = await hook.post("/api/webhooks/stripe", content=payload)
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_webhook_signature"


async def test_checkout_session_completed_starts_active_creates_schedule_purges_q3_q5_locks_quiz(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    sub = await _status(pclient)
    assert sub["status"] == "active" and sub["source"] == "stripe"
    assert sub["planId"] == "four_week" and sub["renewalCount"] == 0
    assert (await pclient.get("/api/_test/gated")).status_code == 200
    [history] = await _rows(
        session_factory,
        "SELECT from_status, to_status, event, source, at FROM subscription_history",
    )
    assert history[:4] == ("none", "active", "started", "stripe")
    [(consent_at,)] = await _rows(
        session_factory, "SELECT auto_renew_consent_at FROM subscriptions"
    )
    assert consent_at is not None and consent_at <= history[4]  # consent stored before the start
    [quiz] = await _rows(
        session_factory, "SELECT answers, locked, health_answers_purged_at FROM quiz_states"
    )
    assert "q3_situation" not in quiz[0] and "q5_changes" not in quiz[0]
    assert quiz[1] is True and quiz[2] is not None
    assert await _rows(session_factory, "SELECT lesson_id FROM lesson_schedule")
    r = await pclient.put("/api/quiz/answers/q6_living", json={"value": "far"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "quiz_locked"


@pytest.mark.parametrize("webhook_first", [True, False])
async def test_reconcile_then_webhook_and_webhook_then_reconcile_start_once(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
    webhook_first: bool,
) -> None:
    checkout_id = await _checkout(pclient)
    sid = await _session_id(session_factory)
    gateway.pay(checkout_id)
    event = stripe_fake.checkout_completed(sid, CUSTOMER, f"sub_fake_{checkout_id}")

    async def reconcile() -> None:
        r = await pclient.get(f"/api/billing/checkout/{checkout_id}")
        assert r.status_code == 200 and r.json()["paid"] is True

    async def webhook() -> None:
        assert (await _send(hook, event)).status_code == 200

    first, second = (webhook, reconcile) if webhook_first else (reconcile, webhook)
    await first()
    [(purged_at,)] = await _rows(
        session_factory, "SELECT health_answers_purged_at FROM quiz_states"
    )
    schedule = await _rows(session_factory, "SELECT lesson_id, seq FROM lesson_schedule")
    await second()

    assert (await _status(pclient))["status"] == "active"
    assert len(await _rows(session_factory, "SELECT * FROM subscription_history")) == 1
    assert await _rows(session_factory, "SELECT lesson_id, seq FROM lesson_schedule") == schedule
    assert await _rows(
        session_factory, "SELECT health_answers_purged_at, locked FROM quiz_states"
    ) == [(purged_at, True)]
    assert purged_at is not None


async def test_duplicate_event_id_processed_once(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    renewal = stripe_fake.invoice_paid(CUSTOMER, SUBSCRIPTION, PERIOD_END, event_id="evt_dup")
    assert (await _send(hook, renewal)).status_code == 200
    assert (await _send(hook, renewal)).status_code == 200
    assert (await _status(pclient))["renewalCount"] == 1
    assert len(await _rows(session_factory, "SELECT * FROM subscription_history")) == 2
    [event] = await _rows(
        session_factory,
        "SELECT event_id, type, processed_at FROM stripe_events WHERE event_id = 'evt_dup'",
    )
    assert event[1] == "invoice.paid" and event[2] is not None


async def test_invoice_paid_first_payment_and_renewal_increment_renewal_count_correctly(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    first = stripe_fake.invoice_paid(CUSTOMER, SUBSCRIPTION, PERIOD_END, first=True)
    assert (await _send(hook, first)).status_code == 200
    assert (await _status(pclient))["renewalCount"] == 0  # the first payment is the start
    sub: dict[str, Any] = {}
    for expected, end in ((1, PERIOD_END), (2, PERIOD_END + timedelta(days=28))):
        renewal = stripe_fake.invoice_paid(CUSTOMER, SUBSCRIPTION, end)
        assert (await _send(hook, renewal)).status_code == 200
        sub = await _status(pclient)
        assert sub["renewalCount"] == expected and sub["status"] == "active"
    assert sub["currentPeriodEnd"].startswith("2026-03-30")


async def test_invoice_payment_failed_sets_past_due_and_gate_returns_402_past_due(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    failed = stripe_fake.invoice_payment_failed(CUSTOMER, SUBSCRIPTION, PERIOD_END)
    assert (await _send(hook, failed)).status_code == 200
    assert (await _status(pclient))["status"] == "past_due"
    r = await pclient.get("/api/_test/gated")
    assert r.status_code == 402 and r.json()["error"]["details"]["reason"] == "past_due"
    [_, entry] = await _rows(
        session_factory,
        "SELECT from_status, to_status, event, source FROM subscription_history ORDER BY id",
    )
    assert entry == ("active", "past_due", "payment_failed", "stripe")


async def test_later_invoice_paid_returns_to_active(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    await _send(hook, stripe_fake.invoice_payment_failed(CUSTOMER, SUBSCRIPTION, PERIOD_END))
    paid = stripe_fake.invoice_paid(CUSTOMER, SUBSCRIPTION, PERIOD_END)
    assert (await _send(hook, paid)).status_code == 200
    sub = await _status(pclient)
    assert sub["status"] == "active" and sub["renewalCount"] == 1
    assert (await pclient.get("/api/_test/gated")).status_code == 200


async def test_subscription_deleted_sets_canceled_and_gate_returns_402_no_subscription(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    deleted = stripe_fake.subscription_event(
        "customer.subscription.deleted", CUSTOMER, SUBSCRIPTION
    )
    assert (await _send(hook, deleted)).status_code == 200
    assert (await _status(pclient))["status"] == "canceled"
    r = await pclient.get("/api/_test/gated")
    assert r.status_code == 402 and r.json()["error"]["details"]["reason"] == "no_subscription"


async def test_subscription_updated_with_cancel_at_period_end_sets_canceling(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    plain = stripe_fake.subscription_event("customer.subscription.updated", CUSTOMER, SUBSCRIPTION)
    assert (await _send(hook, plain)).status_code == 200
    assert (await _status(pclient))["status"] == "active"  # no cancel flag: nothing changes
    cancel = stripe_fake.subscription_event(
        "customer.subscription.updated", CUSTOMER, SUBSCRIPTION, cancel_at_period_end=True
    )
    assert (await _send(hook, cancel)).status_code == 200
    assert (await _status(pclient))["status"] == "canceling"
    assert (await pclient.get("/api/_test/gated")).status_code == 200  # access until period end


async def test_test_clock_ready_event_is_acknowledged_and_recorded(
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    r = await _send(hook, stripe_fake.test_clock_ready())
    assert r.status_code == 200 and r.json() == {"received": True}
    [(event_type, processed_at)] = await _rows(
        session_factory, "SELECT type, processed_at FROM stripe_events"
    )
    assert event_type == "test_helpers.test_clock.ready" and processed_at is not None


async def test_unknown_event_type_returns_200_and_is_recorded(
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    r = await _send(hook, stripe_fake.event("charge.refunded", {"id": "ch_1"}, "evt_unknown_1"))
    assert r.status_code == 200
    assert await _rows(session_factory, "SELECT event_id, type FROM stripe_events") == [
        ("evt_unknown_1", "charge.refunded")
    ]


async def test_event_for_unknown_session_returns_200_without_side_effects(
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ghost = UUID(int=99)
    events = [
        stripe_fake.checkout_completed(ghost, "cus_ghost", "sub_ghost"),
        stripe_fake.invoice_paid("cus_ghost", "sub_ghost", PERIOD_END, session_id=ghost),
        stripe_fake.subscription_event("customer.subscription.deleted", "cus_ghost", "sub_ghost"),
    ]
    for event in events:
        assert (await _send(hook, event)).status_code == 200
    assert await _rows(session_factory, "SELECT * FROM subscriptions") == []
    assert await _rows(session_factory, "SELECT * FROM subscription_history") == []
    assert len(await _rows(session_factory, "SELECT * FROM stripe_events")) == 3


async def test_event_resolves_session_by_stored_customer_id_without_metadata(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    failed = stripe_fake.invoice_payment_failed(CUSTOMER, SUBSCRIPTION, PERIOD_END)  # no session id
    assert (await _send(hook, failed)).status_code == 200
    assert (await _status(pclient))["status"] == "past_due"


async def test_webhook_route_does_not_require_a_session_token(
    hook: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    assert "X-Session-Token" not in hook.headers
    assert (await _send(hook, stripe_fake.test_clock_ready())).status_code == 200
