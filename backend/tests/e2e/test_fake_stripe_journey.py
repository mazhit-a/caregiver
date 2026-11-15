"""The in-app fake Stripe through the real app and Postgres (no Coach or Stripe fakes needed:
`FAKE_STRIPE=true` replaces the payment gateway, nothing touches the network)."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.config import Settings
from app.infrastructure.content.provider import JsonContentProvider
from app.main import create_app
from tests.e2e.journey import answer_quiz_persona_b, ok
from tests.fakes.clock import FixedClock
from tests.fakes.roleplay import FakeCoach
from tests.lesson_content import REPO

GOOD = {"cardNumber": "4242 4242 4242 4242", "expMonth": 12, "expYear": 2030, "cvc": "123"}


@pytest.fixture
async def fake_app(
    test_database_url: str, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[FastAPI]:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url=test_database_url,
        stripe_secret_key="sk_test_realistic123",  # a key exists: the fake still wins
        anthropic_api_key="dummy",
        fake_stripe=True,
        public_app_url="http://app.test",
    )
    app = create_app(settings)
    app.state.clock = FixedClock()
    app.state.content = JsonContentProvider.from_directory(REPO / "content")
    app.state.coach = FakeCoach()
    yield app
    await app.state.engine.dispose()


@pytest.fixture
async def learner(fake_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=fake_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/session")
        assert r.status_code == 201, r.text
        c.headers["X-Session-Token"] = r.json()["token"]
        yield c


@pytest.fixture
async def anonymous(fake_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=fake_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _start_checkout(learner: httpx.AsyncClient) -> str:
    await answer_quiz_persona_b(learner)
    body = await ok(await learner.post("/api/billing/checkout", json={"autoRenewConsent": True}))
    assert body["url"] == f"http://app.test/fake-checkout/{body['checkoutId']}"
    assert body["checkoutId"].startswith("cs_fake_")
    return str(body["checkoutId"])


async def _subscription(client: httpx.AsyncClient) -> dict[str, Any]:
    body: dict[str, Any] = await ok(await client.get("/api/billing/subscription"))
    return body


async def test_fake_checkout_journey_pay_reconcile_and_gated_access(
    learner: httpx.AsyncClient, anonymous: httpx.AsyncClient
) -> None:
    checkout_id = await _start_checkout(learner)
    base = f"/api/fake-stripe/checkout/{checkout_id}"
    summary = await ok(await anonymous.get(base))  # the page needs no session token
    assert summary["fake"] is True and summary["status"] == "open"
    assert summary["amountToday"] > 0 and summary["renewalPrice"] > 0 and summary["planLabel"]
    assert summary["successUrl"] == f"http://app.test/checkout/return?checkout_id={checkout_id}"
    assert summary["cancelUrl"] == "http://app.test/paywall?checkout=canceled"

    unpaid = await ok(await learner.get(f"/api/billing/checkout/{checkout_id}"))
    assert unpaid["paid"] is False and unpaid["subscription"]["status"] == "none"
    assert (await learner.get("/api/lessons/m1_l1")).status_code == 402

    paid = await ok(await anonymous.post(f"{base}/pay", json=GOOD))
    assert paid == {"fake": True, "status": "paid", "successUrl": summary["successUrl"]}
    reconciled = await ok(await learner.get(f"/api/billing/checkout/{checkout_id}"))
    assert reconciled["paid"] is True
    sub = await _subscription(learner)
    assert sub["status"] == "active" and sub["source"] == "stripe" and sub["renewalCount"] == 0
    assert (await learner.get("/api/lessons/m1_l1")).status_code == 200
    again = await ok(await anonymous.post(f"{base}/pay", json=GOOD))  # idempotent
    assert again["status"] == "paid"
    assert (await _subscription(learner))["renewalCount"] == 0


@pytest.mark.parametrize(
    ("card", "code", "decline"),
    [
        ("4000000000000002", "card_declined", "generic_decline"),
        ("4000000000009995", "card_declined", "insufficient_funds"),
        ("4000000000000069", "expired_card", "expired_card"),
        ("4000000000000127", "incorrect_cvc", "incorrect_cvc"),
        ("4111111111111111", "card_declined", "generic_decline"),
    ],
)
async def test_declined_cards_answer_402_and_leave_no_subscription(
    learner: httpx.AsyncClient, anonymous: httpx.AsyncClient, card: str, code: str, decline: str
) -> None:
    checkout_id = await _start_checkout(learner)
    r = await anonymous.post(
        f"/api/fake-stripe/checkout/{checkout_id}/pay", json={**GOOD, "cardNumber": card}
    )
    assert r.status_code == 402, r.text
    error = r.json()["error"]
    assert error["code"] == code and error["message"]
    assert error["details"] == {"declineCode": decline, "fake": True}
    assert (await _subscription(learner))["status"] == "none"
    reconciled = await ok(await learner.get(f"/api/billing/checkout/{checkout_id}"))
    assert reconciled["paid"] is False
    assert (await learner.get("/api/lessons/m1_l1")).status_code == 402


async def test_expired_date_and_bad_cvc_are_refused_for_the_good_card(
    learner: httpx.AsyncClient, anonymous: httpx.AsyncClient
) -> None:
    checkout_id = await _start_checkout(learner)
    pay = f"/api/fake-stripe/checkout/{checkout_id}/pay"
    r = await anonymous.post(pay, json={**GOOD, "expMonth": 1, "expYear": 2020})
    assert r.status_code == 402 and r.json()["error"]["code"] == "expired_card"
    r = await anonymous.post(pay, json={**GOOD, "cvc": "12"})
    assert r.status_code == 402 and r.json()["error"]["code"] == "incorrect_cvc"
    r = await anonymous.post(pay, json={**GOOD, "expMonth": 13})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert (await _subscription(learner))["status"] == "none"


async def test_three_d_secure_card_needs_the_authenticate_step(
    learner: httpx.AsyncClient, anonymous: httpx.AsyncClient
) -> None:
    checkout_id = await _start_checkout(learner)
    pay = f"/api/fake-stripe/checkout/{checkout_id}/pay"
    card = {**GOOD, "cardNumber": "4000 0025 0000 3155"}
    first = await ok(await anonymous.post(pay, json=card))
    assert first["status"] == "requires_action"
    assert (await _subscription(learner))["status"] == "none"
    done = await ok(await anonymous.post(pay, json={**card, "authenticated": True}))
    assert done["status"] == "paid"
    assert (await _subscription(learner))["status"] == "active"


async def test_cancel_returns_to_unpaid_and_the_checkout_is_closed(
    learner: httpx.AsyncClient, anonymous: httpx.AsyncClient
) -> None:
    checkout_id = await _start_checkout(learner)
    base = f"/api/fake-stripe/checkout/{checkout_id}"
    canceled = await ok(await anonymous.post(f"{base}/cancel"))
    assert canceled == {
        "fake": True,
        "status": "canceled",
        "cancelUrl": "http://app.test/paywall?checkout=canceled",
    }
    assert (await ok(await learner.get(f"/api/billing/checkout/{checkout_id}")))["paid"] is False
    assert (await _subscription(learner))["status"] == "none"
    r = await anonymous.post(f"{base}/pay", json=GOOD)
    assert r.status_code == 409 and r.json()["error"]["code"] == "checkout_closed"
    # a fresh checkout still works afterwards
    fresh = await ok(await learner.post("/api/billing/checkout", json={"autoRenewConsent": True}))
    r = await anonymous.post(f"/api/fake-stripe/checkout/{fresh['checkoutId']}/pay", json=GOOD)
    assert r.status_code == 200


async def test_unknown_checkout_is_404_on_all_three_endpoints(
    anonymous: httpx.AsyncClient,
) -> None:
    base = "/api/fake-stripe/checkout/cs_fake_unknown"
    for r in (
        await anonymous.get(base),
        await anonymous.post(f"{base}/pay", json=GOOD),
        await anonymous.post(f"{base}/cancel"),
    ):
        assert r.status_code == 404 and r.json()["error"]["code"] == "checkout_not_found"


async def test_checkout_of_another_session_cannot_be_reconciled(
    fake_app: FastAPI, learner: httpx.AsyncClient
) -> None:
    checkout_id = await _start_checkout(learner)
    transport = httpx.ASGITransport(app=fake_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as other:
        token = (await other.post("/api/session")).json()["token"]
        other.headers["X-Session-Token"] = token
        r = await other.get(f"/api/billing/checkout/{checkout_id}")
        assert r.status_code == 404


async def test_demo_controls_work_with_the_fake_subscription_and_renewal_goes_through_events(
    learner: httpx.AsyncClient,
    anonymous: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    checkout_id = await _start_checkout(learner)
    await ok(await anonymous.post(f"/api/fake-stripe/checkout/{checkout_id}/pay", json=GOOD))
    state = await ok(await learner.post("/api/demo/jump-to-renewal"))
    assert state["billingSync"] == "done"  # the fake emitted test_clock.ready
    sub = await _subscription(learner)
    assert sub["status"] == "active" and sub["renewalCount"] == 1
    await ok(await learner.post("/api/demo/fail-next-payment"))
    await ok(await learner.post("/api/demo/jump-to-renewal"))
    assert (await _subscription(learner))["status"] == "past_due"
    async with session_factory() as db:
        types = (
            await db.execute(text("SELECT type FROM stripe_events ORDER BY received_at"))
        ).all()
    assert {t[0] for t in types} >= {
        "checkout.session.completed",
        "invoice.paid",
        "invoice.payment_failed",
        "test_helpers.test_clock.ready",
    }


async def test_card_numbers_never_reach_the_database(
    learner: httpx.AsyncClient,
    anonymous: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    checkout_id = await _start_checkout(learner)
    await ok(await anonymous.post(f"/api/fake-stripe/checkout/{checkout_id}/pay", json=GOOD))
    async with session_factory() as db:
        dump = (
            await db.execute(
                text(
                    "SELECT row_to_json(s)::text FROM subscriptions s UNION ALL "
                    "SELECT row_to_json(e)::text FROM stripe_events e UNION ALL "
                    "SELECT row_to_json(h)::text FROM subscription_history h"
                )
            )
        ).all()
    assert "4242" not in " ".join(row[0] for row in dump)
    assert checkout_id not in " ".join(row[0] for row in dump)


async def test_fake_endpoints_are_not_mounted_when_fake_stripe_is_off(
    db_app: FastAPI,
) -> None:
    transport = httpx.ASGITransport(app=db_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        for r in (
            await c.get("/api/fake-stripe/checkout/cs_fake_x"),
            await c.post("/api/fake-stripe/checkout/cs_fake_x/pay", json=GOOD),
            await c.post("/api/fake-stripe/checkout/cs_fake_x/cancel"),
        ):
            assert r.status_code == 404
    assert db_app.state.payment_gateway is None  # dummy key: no gateway, and never the fake
    assert not hasattr(db_app.state, "fake_checkout_store")


def test_fake_mode_logs_a_startup_warning_and_uses_the_fake_gateway(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from app.infrastructure.payments.fake_stripe import FakeStripeGateway

    with caplog.at_level("WARNING"):
        app = create_app(
            Settings(_env_file=None, fake_stripe=True, stripe_secret_key="sk_test_real")  # type: ignore[call-arg]
        )
    assert isinstance(app.state.payment_gateway, FakeStripeGateway)
    assert any("FAKE_STRIPE" in r.getMessage() for r in caplog.records)
