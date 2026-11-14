"""Increment 36: cancel preview and cancel, Test Clock sync for the demo controls, failing payment.

The gateway is `FakePaymentGateway` and webhooks are signed with `FakeStripe`: no network.
"""

from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.billing.errors import PaymentGatewayError
from tests.fakes.payments import FakePaymentGateway
from tests.fakes.stripe_webhooks import FakeStripe
from tests.presentation import test_stripe_webhooks_api as hooks
from tests.presentation.test_billing_api import NOW, _answer_and_complete, _force_status

# Fixtures shared with the billing and webhook API tests.
content = hooks.content
pclient = hooks.pclient
gateway = hooks.gateway
hook = hooks.hook

stripe_fake = FakeStripe()
_send = hooks._send
_start_via_webhook = hooks._start_via_webhook
CLOCK = "clock_fake_1"
FIRST_PERIOD_END = datetime(2026, 2, 2, 9, 0, tzinfo=UTC)  # the start: app now + intro days


async def _demo_subscribe(client: httpx.AsyncClient) -> None:
    await _answer_and_complete(client)
    r = await client.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 200, r.text


def _advances(gateway: FakePaymentGateway) -> list[datetime]:
    return [args[1] for name, args in gateway.calls if name == "advance_test_clock"]


# --- cancel preview ---------------------------------------------------------------------------


async def test_cancel_preview_lists_plan_phrase_count_card_status_end_date_and_no_discount_field(
    pclient: httpx.AsyncClient,
) -> None:
    await _demo_subscribe(pclient)
    for body in ("One", "Two", "Three"):
        r = await pclient.post("/api/phrases", json={"text": body, "source": "scenario"})
        assert r.status_code in (200, 201), r.text
    r = await pclient.get("/api/billing/cancel-preview")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"planName", "savedPhraseCount", "careCardPublished", "endDate", "status"}
    assert body["planName"] and body["savedPhraseCount"] == 3
    assert body["careCardPublished"] is False
    assert (
        body["endDate"]
        == (await pclient.get("/api/billing/subscription")).json()["currentPeriodEnd"]
    )
    published = await pclient.post("/api/care-card", json={})
    assert published.status_code in (200, 201), published.text
    after = (await pclient.get("/api/billing/cancel-preview")).json()
    assert after["careCardPublished"] is True
    assert not any("discount" in key.lower() or "offer" in key.lower() for key in after)


async def test_cancel_copy_has_no_retention_offer_words(
    pclient: httpx.AsyncClient,
) -> None:
    await _demo_subscribe(pclient)
    preview = (await pclient.get("/api/billing/cancel-preview")).text
    cancel = (await pclient.post("/api/billing/cancel")).text
    for words in (preview, cancel):
        lowered = words.lower()
        for banned in ("discount", "offer", "coupon", "% off", "stay", "pause", "special", "deal"):
            assert banned not in lowered, banned


# --- cancel -----------------------------------------------------------------------------------


async def test_cancel_sets_canceling_and_access_continues_until_period_end_then_402(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _demo_subscribe(pclient)
    end = (await pclient.get("/api/billing/subscription")).json()["currentPeriodEnd"]
    r = await pclient.post("/api/billing/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "canceling" and r.json()["endDate"] == end
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "canceling"
    assert (await pclient.get("/api/_test/gated")).status_code == 200
    await pclient.post("/api/demo/jump-to-renewal")  # app time passes the period end
    gated = await pclient.get("/api/_test/gated")
    assert gated.status_code == 402
    assert gated.json()["error"]["details"]["reason"] == "no_subscription"
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "canceled"
    async with session_factory() as db:
        events = (
            await db.execute(text("SELECT event FROM subscription_history ORDER BY id"))
        ).scalars()
        assert list(events) == ["started", "cancel_requested", "period_ended"]


async def test_cancel_for_stripe_session_calls_cancel_at_period_end(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    r = await pclient.post("/api/billing/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "canceling"
    assert r.json()["endDate"].startswith("2026-02-02")
    assert ("cancel_at_period_end", hooks.SUBSCRIPTION) in gateway.calls
    # the later `customer.subscription.updated` webhook is a no-op
    event = stripe_fake.subscription_event(
        "customer.subscription.updated", hooks.CUSTOMER, hooks.SUBSCRIPTION, None, True
    )
    assert (await _send(hook, event)).status_code == 200
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "canceling"


async def test_cancel_when_stripe_fails_returns_502_with_demo_hint_and_changes_nothing(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    gateway.fail_with = PaymentGatewayError()
    r = await pclient.post("/api/billing/cancel")
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "payment_gateway_error"
    assert r.json()["error"]["details"]["hint"] == "demo_mode"
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "active"
    rows = await _history(session_factory)
    assert rows == ["started"]


async def _history(factory: async_sessionmaker[AsyncSession]) -> list[str]:
    async with factory() as db:
        return list(
            (await db.execute(text("SELECT event FROM subscription_history ORDER BY id"))).scalars()
        )


async def test_cancel_with_no_subscription_409(pclient: httpx.AsyncClient) -> None:
    r = await pclient.post("/api/billing/cancel")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "no_active_subscription"
    assert (await pclient.get("/api/billing/cancel-preview")).status_code == 409


async def test_cancel_twice_second_call_409_status_unchanged(pclient: httpx.AsyncClient) -> None:
    await _demo_subscribe(pclient)
    assert (await pclient.post("/api/billing/cancel")).status_code == 200
    again = await pclient.post("/api/billing/cancel")
    assert again.status_code == 409
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "canceling"


# --- Test Clock sync --------------------------------------------------------------------------


async def test_checkout_stores_the_test_clock_id(
    pclient: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await hooks._checkout(pclient)
    async with session_factory() as db:
        row = (
            await db.execute(
                text(
                    "SELECT stripe_test_clock_id, stripe_clock_at, billing_sync FROM subscriptions"
                )
            )
        ).one()
    assert tuple(row) == (CLOCK, NOW, "none")


async def test_next_day_for_stripe_session_advances_clock_forward_only_and_returns_billing_sync_pending(  # noqa: E501
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    assert (await pclient.get("/api/billing/subscription")).json()["billingSync"] == "none"
    first = await pclient.post("/api/demo/next-day")
    assert first.status_code == 200, first.text
    assert first.json()["billingSync"] == "pending"
    assert (await pclient.get("/api/billing/subscription")).json()["billingSync"] == "pending"
    second = await pclient.post("/api/demo/next-day")
    assert second.json()["billingSync"] == "pending"
    assert _advances(gateway) == [NOW + timedelta(days=1), NOW + timedelta(days=2)]
    # a jump whose target is before the clock's current time must not move the clock back
    for _ in range(40):
        await pclient.post("/api/demo/next-day")
    clock_time = _advances(gateway)[-1]
    calls_before = len(gateway.calls)
    jumped = await pclient.post("/api/demo/jump-to-renewal")  # period end + 1h is in the past
    assert jumped.status_code == 200
    assert len(gateway.calls) == calls_before
    assert all(b > a for a, b in zip(_advances(gateway), _advances(gateway)[1:], strict=False))
    assert _advances(gateway)[-1] == clock_time


async def test_jump_to_renewal_for_stripe_session_advances_clock_to_period_end_plus_one_hour(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    r = await pclient.post("/api/demo/jump-to-renewal")
    assert r.status_code == 200 and r.json()["billingSync"] == "pending"
    assert _advances(gateway) == [FIRST_PERIOD_END + timedelta(hours=1)]
    assert (await pclient.get("/api/demo")).json()["billingSync"] == "pending"


async def test_next_day_for_demo_session_never_touches_stripe_and_billing_sync_is_none(
    pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    await _demo_subscribe(pclient)
    r = await pclient.post("/api/demo/next-day")
    assert r.json()["billingSync"] == "none"
    assert (await pclient.post("/api/demo/jump-to-renewal")).json()["billingSync"] == "none"
    assert gateway.calls == []
    assert (await pclient.get("/api/billing/subscription")).json()["billingSync"] == "none"


async def test_next_day_when_stripe_fails_returns_502_and_keeps_the_clock_and_sync(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    gateway.fail_with = PaymentGatewayError()
    r = await pclient.post("/api/demo/next-day")
    assert r.status_code == 502
    gateway.fail_with = None
    state = (await pclient.get("/api/demo")).json()
    assert state["clockOffsetSeconds"] == 0 and state["billingSync"] == "none"
    # the failed attempt did not move the stored clock time: the retry is still forward
    assert (await pclient.post("/api/demo/next-day")).json()["billingSync"] == "pending"


async def test_clock_ready_webhook_sets_billing_sync_done(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    await pclient.post("/api/demo/next-day")
    assert (await _send(hook, stripe_fake.test_clock_ready(CLOCK))).status_code == 200
    assert (await pclient.get("/api/billing/subscription")).json()["billingSync"] == "done"
    assert (await pclient.get("/api/demo")).json()["billingSync"] == "done"
    # the next advance is pending again; a ready event for another clock changes nothing
    await pclient.post("/api/demo/next-day")
    assert (await _send(hook, stripe_fake.test_clock_ready("clock_other"))).status_code == 200
    assert (await pclient.get("/api/billing/subscription")).json()["billingSync"] == "pending"


# --- failing payment --------------------------------------------------------------------------


async def test_fail_next_payment_then_renewal_gives_past_due_and_402_past_due(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    r = await pclient.post("/api/demo/fail-next-payment")
    assert r.status_code == 200, r.text
    assert ("attach_failing_payment_method", hooks.CUSTOMER) in gateway.calls
    await pclient.post("/api/demo/jump-to-renewal")
    # Stripe would now try the renewal charge and send this event
    failed = stripe_fake.invoice_payment_failed(
        hooks.CUSTOMER, hooks.SUBSCRIPTION, hooks.PERIOD_END
    )
    assert (await _send(hook, failed)).status_code == 200
    assert (await _send(hook, stripe_fake.test_clock_ready(CLOCK))).status_code == 200
    sub = (await pclient.get("/api/billing/subscription")).json()
    assert sub["status"] == "past_due" and sub["billingSync"] == "done"
    gated = await pclient.get("/api/_test/gated")
    assert gated.status_code == 402 and gated.json()["error"]["details"]["reason"] == "past_due"


async def test_fail_next_payment_disabled_without_demo_controls(
    db_app: FastAPI, pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    from app.presentation.api.deps import AppInfo

    db_app.state.app_info = AppInfo(demo_controls=False)
    r = await pclient.post("/api/demo/fail-next-payment")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    assert gateway.calls == []


async def test_fail_next_payment_for_demo_or_missing_subscription_409(
    pclient: httpx.AsyncClient, gateway: FakePaymentGateway
) -> None:
    r = await pclient.post("/api/demo/fail-next-payment")
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_a_stripe_subscription"
    await _demo_subscribe(pclient)
    assert (await pclient.post("/api/demo/fail-next-payment")).status_code == 409
    assert gateway.calls == []


async def test_cancel_preview_cancel_and_subscription_endpoints_reachable_when_past_due(
    pclient: httpx.AsyncClient,
    hook: httpx.AsyncClient,
    gateway: FakePaymentGateway,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _start_via_webhook(pclient, hook, session_factory)
    failed = stripe_fake.invoice_payment_failed(
        hooks.CUSTOMER, hooks.SUBSCRIPTION, hooks.PERIOD_END
    )
    await _send(hook, failed)
    assert (await pclient.get("/api/_test/gated")).status_code == 402
    assert (await pclient.get("/api/pricing")).status_code == 200
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "past_due"
    preview = await pclient.get("/api/billing/cancel-preview")
    assert preview.status_code == 200 and preview.json()["status"] == "past_due"
    assert (await pclient.get("/api/demo")).status_code == 200
    assert (await pclient.post("/api/demo/next-day")).status_code == 200
    assert (await pclient.get("/api/resources/crisis")).status_code == 200
    # past_due cannot be canceled here (409, not the gate's 402): gentle exit is the way out
    cancel = await pclient.post("/api/billing/cancel")
    assert cancel.status_code == 409 and cancel.json()["error"]["code"] == "no_active_subscription"


async def test_demo_session_endpoints_reachable_in_every_status(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _answer_and_complete(pclient)
    await _force_status(session_factory, "past_due")
    for path in ("/api/billing/cancel-preview", "/api/billing/subscription", "/api/pricing"):
        assert (await pclient.get(path)).status_code == 200, path
