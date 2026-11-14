"""Increment 37: gentle exit and "Clear my data" over the real app and Postgres.

The payment gateway is `FakePaymentGateway`: no network. A failing cancellation must delete nothing.
"""

import re

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.billing.errors import PaymentGatewayError
from tests.fakes.payments import FakePaymentGateway
from tests.presentation import test_stripe_webhooks_api as hooks
from tests.presentation.test_billing_api import (
    _answer_and_complete,
    _force_status,
    _session_id,
)

content = hooks.content
pclient = hooks.pclient
gateway = hooks.gateway
hook = hooks.hook
_start_via_webhook = hooks._start_via_webhook

BANNED = (
    "discount",
    "offer",
    "coupon",
    "% off",
    "stay",
    "pause",
    "special",
    "deal",
    "come back",
    "before you go",
    "reconsider",
    "miss you",
    "sale",
)
ENDPOINTS = (("post", "/api/exit/gentle"), ("delete", "/api/session"))


async def _add_data(client: httpx.AsyncClient) -> str:
    """Phrases, a profile and a published care card; returns the care card id."""
    for body in ("One", "Two"):
        r = await client.post("/api/phrases", json={"text": body, "source": "scenario"})
        assert r.status_code in (200, 201), r.text
    r = await client.put("/api/profile", json={"displayName": "Margaret", "calms": ["tea"]})
    assert r.status_code == 200, r.text
    published = await client.post("/api/care-card", json={})
    assert published.status_code in (200, 201), published.text
    link = str(published.json()["link"])
    return link.rstrip("/").rsplit("/", 1)[-1]


async def _count(factory: async_sessionmaker[AsyncSession], table: str) -> int:
    async with factory() as db:
        return int(await db.scalar(text(f"SELECT count(*) FROM {table}")) or 0)  # noqa: S608


async def _status_in_db(factory: async_sessionmaker[AsyncSession]) -> tuple[object, ...]:
    async with factory() as db:
        row = (
            await db.execute(
                text("SELECT status, source, stripe_subscription_id FROM subscriptions")
            )
        ).one()
    return tuple(row)


async def _stripe_session_with_data(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    factory: async_sessionmaker[AsyncSession],
) -> str:
    await _start_via_webhook(pclient, hook, factory)
    return await _add_data(pclient)


# --- gentle exit ------------------------------------------------------------------------------


async def test_gentle_exit_response_has_condolence_text_resources_and_no_retention_copy(
    pclient: httpx.AsyncClient,
) -> None:
    await _answer_and_complete(pclient)
    assert (
        await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    ).status_code == 200
    r = await pclient.post("/api/exit/gentle")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"title", "condolence", "resourcesIntro", "resources"}
    assert body["condolence"] and body["resourcesIntro"]
    assert len(body["resources"]) >= 2
    assert all(res["name"] and (res["phone"] or res["url"]) for res in body["resources"])
    assert not re.search(r"\{[A-Za-z]+\}", r.text)
    lowered = r.text.lower()
    for banned in BANNED:
        assert banned not in lowered, banned


async def test_gentle_exit_copy_in_content_has_no_retention_words(
    content: object,
) -> None:
    from app.infrastructure.content.provider import JsonContentProvider

    assert isinstance(content, JsonContentProvider)
    copy = content.gentle_exit_copy()
    texts = [copy.title, copy.condolence, copy.resources_intro, copy.clear_data_confirmation]
    texts += [f"{r.name} {r.description}" for r in copy.resources]
    for text_ in texts:
        for banned in BANNED:
            assert banned not in text_.lower(), (banned, text_)


async def test_gentle_exit_cancels_stripe_subscription_immediately_no_proration(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _stripe_session_with_data(pclient, hook, session_factory)
    before = len(gateway.calls)
    r = await pclient.post("/api/exit/gentle")
    assert r.status_code == 200, r.text
    # Exactly one provider call: an immediate cancel (the adapter sends a bare DELETE, i.e. no
    # proration and no final invoice; see test_stripe_gateway), never cancel_at_period_end.
    assert gateway.calls[before:] == [("cancel_now", hooks.SUBSCRIPTION)]


async def test_gentle_exit_then_care_card_public_route_returns_404(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    card_id = await _stripe_session_with_data(pclient, hook, session_factory)
    assert (await hook.get(f"/api/cards/{card_id}")).status_code == 200
    assert (await pclient.post("/api/exit/gentle")).status_code == 200
    assert (await hook.get(f"/api/cards/{card_id}")).status_code == 404
    assert await _count(session_factory, "care_cards") == 0


async def test_old_token_returns_401_after_clear(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _answer_and_complete(pclient)
    r = await pclient.delete("/api/session")
    assert r.status_code == 200 and r.json()["message"]
    assert (await pclient.get("/api/billing/subscription")).status_code == 401
    assert (await pclient.delete("/api/session")).status_code == 401
    assert await _count(session_factory, "sessions") == 0


async def test_old_token_returns_401_after_gentle_exit(pclient: httpx.AsyncClient) -> None:
    assert (await pclient.post("/api/exit/gentle")).status_code == 200
    assert (await pclient.get("/api/billing/subscription")).status_code == 401


# --- the cancel-at-provider rule --------------------------------------------------------------


async def test_delete_session_cancels_active_subscription_first(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    seen: list[int] = []
    original = gateway.cancel_now

    async def spying_cancel_now(subscription_id: str) -> None:
        seen.append(await _count(session_factory, "sessions"))  # still there when we cancel
        await original(subscription_id)

    gateway.cancel_now = spying_cancel_now  # type: ignore[method-assign]
    r = await pclient.delete("/api/session")
    assert r.status_code == 200, r.text
    assert seen == [1]
    assert ("cancel_now", hooks.SUBSCRIPTION) in gateway.calls
    assert await _count(session_factory, "sessions") == 0


async def test_demo_subscription_needs_no_gateway_call_and_works_without_a_gateway(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    pclient._transport.app.state.payment_gateway = None  # type: ignore[attr-defined]
    await _answer_and_complete(pclient)
    await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert (await pclient.post("/api/exit/gentle")).status_code == 200
    assert await _count(session_factory, "subscriptions") == 0


@pytest.mark.parametrize("status", ["none", "demo", "past_due", "canceling", "canceled", "ended"])
@pytest.mark.parametrize(("method", "url"), ENDPOINTS)
async def test_both_endpoints_are_reachable_for_every_subscription_status(
    status: str,
    method: str,
    url: str,
    pclient: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _answer_and_complete(pclient)
    if status != "none":
        await _force_status(session_factory, status)  # type: ignore[arg-type]
    r = await getattr(pclient, method)(url)
    assert r.status_code == 200, r.text
    assert await _count(session_factory, "sessions") == 0


@pytest.mark.parametrize("status", ["active", "past_due", "canceling"])
async def test_exit_cancels_at_provider_for_every_live_stripe_status(
    status: str,
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    async with session_factory() as db:
        await db.execute(text("UPDATE subscriptions SET status = :s"), {"s": status})
        await db.commit()
    assert (await pclient.post("/api/exit/gentle")).status_code == 200
    assert ("cancel_now", hooks.SUBSCRIPTION) in gateway.calls


async def test_exit_of_an_already_canceled_stripe_subscription_makes_no_provider_call(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    async with session_factory() as db:
        await db.execute(text("UPDATE subscriptions SET status = 'canceled'"))
        await db.commit()
    before = len(gateway.calls)
    assert (await pclient.delete("/api/session")).status_code == 200
    assert len(gateway.calls) == before


# --- a failing cancellation deletes nothing ---------------------------------------------------


async def _assert_nothing_deleted(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    factory: async_sessionmaker[AsyncSession],
    card_id: str,
    subscription_before: tuple[object, ...],
    response: httpx.Response,
) -> None:
    assert response.status_code == 503, response.text
    error = response.json()["error"]
    assert error["code"] == "billing_cancel_failed"
    assert error["message"] and error["details"] == {"retryable": True}
    assert await _count(factory, "sessions") == 1
    assert await _count(factory, "quiz_states") == 1
    assert await _count(factory, "plans") == 1
    assert await _count(factory, "saved_phrases") == 2
    assert await _count(factory, "profiles") == 1
    assert (await hook.get(f"/api/cards/{card_id}")).status_code == 200  # still published
    assert await _status_in_db(factory) == subscription_before
    assert await _count(factory, "subscription_history") == 1  # no `ended` entry
    # the token still works
    assert (await pclient.get("/api/billing/subscription")).status_code == 200


async def test_gentle_exit_when_stripe_cancel_fails_returns_503_billing_cancel_failed_and_keeps_all_rows(  # noqa: E501
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    card_id = await _stripe_session_with_data(pclient, hook, session_factory)
    before = await _status_in_db(session_factory)
    gateway.fail_with = PaymentGatewayError()
    r = await pclient.post("/api/exit/gentle")
    await _assert_nothing_deleted(pclient, hook, session_factory, card_id, before, r)


async def test_clear_data_when_stripe_cancel_fails_returns_503_billing_cancel_failed_and_keeps_all_rows(  # noqa: E501
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    card_id = await _stripe_session_with_data(pclient, hook, session_factory)
    before = await _status_in_db(session_factory)
    gateway.fail_with = PaymentGatewayError()
    r = await pclient.delete("/api/session")
    await _assert_nothing_deleted(pclient, hook, session_factory, card_id, before, r)
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "active"


async def test_clear_data_retry_after_stripe_recovers_deletes_everything(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    card_id = await _stripe_session_with_data(pclient, hook, session_factory)
    gateway.fail_with = PaymentGatewayError()
    assert (await pclient.delete("/api/session")).status_code == 503
    gateway.fail_with = None
    r = await pclient.delete("/api/session")
    assert r.status_code == 200, r.text
    assert ("cancel_now", hooks.SUBSCRIPTION) in gateway.calls
    assert await _count(session_factory, "sessions") == 0
    assert await _count(session_factory, "saved_phrases") == 0
    assert (await hook.get(f"/api/cards/{card_id}")).status_code == 404
    assert (await pclient.get("/api/billing/subscription")).status_code == 401


async def test_gentle_exit_retry_after_stripe_recovers_deletes_everything(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _stripe_session_with_data(pclient, hook, session_factory)
    gateway.fail_with = PaymentGatewayError()
    assert (await pclient.post("/api/exit/gentle")).status_code == 503
    gateway.fail_with = None
    r = await pclient.post("/api/exit/gentle")
    assert r.status_code == 200 and r.json()["condolence"]
    assert await _count(session_factory, "sessions") == 0


async def test_stripe_subscription_without_a_configured_gateway_is_a_retryable_503(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    pclient._transport.app.state.payment_gateway = None  # type: ignore[attr-defined]
    r = await pclient.post("/api/exit/gentle")
    assert r.status_code == 503 and r.json()["error"]["code"] == "billing_cancel_failed"
    assert await _count(session_factory, "sessions") == 1
    assert await _session_id(session_factory)
