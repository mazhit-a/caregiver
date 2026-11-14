"""Increment 40 on the full journey: nothing sensitive in ANY log record at DEBUG, and the Stripe
webhook route is exempt from rate limiting but always signature-verified."""

import logging
from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.config import Settings
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.logging import QUIET_LOGGERS
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.main import create_app
from tests.e2e.journey import REPLY_MARKER
from tests.e2e.test_full_journey import (
    LATER_PHRASE,
    PLAN_RESPONSE,
    SAVED_PHRASE,
    run_demo_journey,
)
from tests.fakes.stripe_webhooks import TEST_WEBHOOK_SECRET, FakeStripe
from tests.lesson_content import REPO

# Built at run time so this file itself never matches the repo secret scan.
FAKE_ANTHROPIC_KEY = "sk-ant-" + "api03-" + "Q" * 40
FAKE_STRIPE_KEY = "sk_test_" + "Z" * 30
FAKE_WEBHOOK_SECRET = "whsec_" + "Y" * 30
PAYLOAD_MARKER = "webhook-payload-marker-8812"


def _all_log_text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(
        f"{r.name} {r.getMessage()} {r.__dict__!r} {r.exc_text}" for r in caplog.records
    )


async def test_logs_never_contain_session_token_reply_text_or_quiz_answers(
    e2e_app: FastAPI,
    learner: httpx.AsyncClient,
    anonymous: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    logging.getLogger("app").setLevel(logging.DEBUG)
    journey = await run_demo_journey(learner, e2e_app, session_factory)
    token = learner.headers["X-Session-Token"]
    # The public card (a bearer id), and signed + unsigned webhooks carrying a marker payload.
    await anonymous.get(f"/api/cards/{journey.card_id}?ref=QUERYMARKER")
    stripe = FakeStripe()
    payload, signature = stripe.event("customer.created", {"id": "cus_1", "note": PAYLOAD_MARKER})
    signed = await anonymous.post(
        "/api/webhooks/stripe", content=payload, headers={"Stripe-Signature": signature}
    )
    assert signed.status_code == 200
    forged = await anonymous.post(
        "/api/webhooks/stripe", content=payload, headers={"Stripe-Signature": "t=1,v1=" + "0" * 64}
    )
    assert forged.status_code == 400

    logs = _all_log_text(caplog)
    assert any(r.name == "app.request" for r in caplog.records), "log capture is not working"
    for secret in (
        token,
        journey.card_id,
        REPLY_MARKER,
        "You sound worried",
        SAVED_PHRASE,
        LATER_PHRASE,
        PLAN_RESPONSE,
        "Margaret",  # profile
        "Slept badly",  # visit sheet
        "At dinner",  # check-in doctor note
        PAYLOAD_MARKER,
        signature,
        "QUERYMARKER",
        'q3_situation": ',
    ):
        assert secret not in logs, secret
    assert "/api/cards/[redacted]" in logs


async def test_no_third_party_logger_is_left_at_debug_for_bodies_or_sql() -> None:
    create_app(Settings(_env_file=None, anthropic_api_key="x"))  # type: ignore[call-arg]
    for name in (*QUIET_LOGGERS, "sqlalchemy.engine", "anthropic._base_client", "httpx"):
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING, name


async def test_api_keys_and_webhook_secret_never_reach_the_logs(
    test_database_url: str,
    session_factory: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    app = create_app(
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            database_url=test_database_url,
            anthropic_api_key=FAKE_ANTHROPIC_KEY,
            stripe_secret_key=FAKE_STRIPE_KEY,
            stripe_webhook_secret=FAKE_WEBHOOK_SECRET,
        )
    )
    app.state.content = JsonContentProvider.from_directory(REPO / "content")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as c:
        await c.get("/api/health")
        r = await c.post("/api/session")
        await c.get("/api/lessons/m1_l1", headers={"X-Session-Token": r.json()["token"]})
        await c.post("/api/webhooks/stripe", content=b"{}", headers={"Stripe-Signature": "bad"})
    await app.state.engine.dispose()
    logs = _all_log_text(caplog)
    assert any(r.name == "app.request" for r in caplog.records)
    for key in (FAKE_ANTHROPIC_KEY, FAKE_STRIPE_KEY, FAKE_WEBHOOK_SECRET):
        assert key not in logs


@pytest.fixture
async def stripe_client(e2e_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=e2e_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_webhook_route_is_exempt_from_rate_limits_but_always_signature_verified(
    e2e_app: FastAPI, stripe_client: httpx.AsyncClient
) -> None:
    tiny = InMemoryRateLimiter(1, timedelta(hours=1))
    for name in (
        "rate_limiter",
        "card_rate_limiter",
        "session_rate_limiter",
        "events_rate_limiter",
    ):
        setattr(e2e_app.state, name, tiny)
    stripe = FakeStripe()
    payload, good = stripe.event("customer.created", {"id": "cus_1"})
    wrong_secret = FakeStripe("whsec_" + "x" * 30).sign(payload)
    for _ in range(60):  # far above every configured limit
        missing = await stripe_client.post("/api/webhooks/stripe", content=payload)
        forged = await stripe_client.post(
            "/api/webhooks/stripe", content=payload, headers={"Stripe-Signature": wrong_secret}
        )
        for r in (missing, forged):
            assert r.status_code == 400, r.text
            assert r.json()["error"]["code"] == "invalid_webhook_signature"
        ok = await stripe_client.post(
            "/api/webhooks/stripe", content=payload, headers={"Stripe-Signature": good}
        )
        assert ok.status_code == 200
    assert TEST_WEBHOOK_SECRET not in missing.text
