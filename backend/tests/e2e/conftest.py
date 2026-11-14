"""Fixtures for the end-to-end tests: the real app and Postgres, the real `content/`, and only the
Coach and the PaymentGateway replaced by fakes."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.payments.webhook_parser import StripeWebhookParser
from tests.fakes.payments import FakePaymentGateway
from tests.fakes.roleplay import FakeCoach
from tests.fakes.stripe_webhooks import TEST_WEBHOOK_SECRET
from tests.lesson_content import REPO


@pytest.fixture
async def e2e_app(db_app: FastAPI) -> FastAPI:
    """`db_app` (real Postgres, settable `FixedClock`) on the real content directory."""
    db_app.state.content = JsonContentProvider.from_directory(REPO / "content")
    db_app.state.coach = FakeCoach()
    db_app.state.payment_gateway = FakePaymentGateway()
    db_app.state.webhook_parser = StripeWebhookParser(TEST_WEBHOOK_SECRET)
    return db_app


@pytest.fixture
async def anonymous(e2e_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """A client without a session token (Stripe webhooks authenticate by signature only)."""
    transport = httpx.ASGITransport(app=e2e_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def learner(e2e_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """A client with a fresh session token, as the browser would hold after `POST /api/session`."""
    transport = httpx.ASGITransport(app=e2e_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/session")
        assert r.status_code == 201, r.text
        c.headers["X-Session-Token"] = r.json()["token"]
        yield c
