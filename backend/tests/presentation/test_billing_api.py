from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.billing.entities import Subscription, SubscriptionStatus
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.presentation.api.deps import CurrentSession, SubscribedSession
from tests.presentation.test_plan_api import PERSONA_B, REPO

NOW = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)

# Temporary routes (not part of the product) to exercise the gate before real routes use it.
_test_router = APIRouter(prefix="/_test")


@_test_router.get("/gated")
async def _gated(session: SubscribedSession) -> dict[str, str]:
    return {"ok": "gated"}


@_test_router.get("/open")
async def _open(session: CurrentSession) -> dict[str, str]:
    return {"ok": "open"}


@pytest.fixture
async def content(db_app: FastAPI) -> JsonContentProvider:
    provider = JsonContentProvider.from_directory(REPO / "content")
    db_app.state.content = provider
    db_app.include_router(_test_router, prefix="/api")
    return provider


@pytest.fixture
async def pclient(
    content: JsonContentProvider, db_client: httpx.AsyncClient
) -> AsyncIterator[httpx.AsyncClient]:
    response = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = response.json()["token"]
    yield db_client


async def _answer_and_complete(client: httpx.AsyncClient) -> None:
    for question, value in PERSONA_B.items():
        r = await client.put(f"/api/quiz/answers/{question}", json={"value": value})
        assert r.status_code == 200, r.text
    assert (await client.post("/api/quiz/complete")).status_code == 200


async def _session_id(factory: async_sessionmaker[AsyncSession]) -> UUID:
    async with factory() as db:
        value = await db.scalar(text("SELECT id FROM sessions"))
    assert isinstance(value, UUID)
    return value


async def _force_status(
    factory: async_sessionmaker[AsyncSession],
    status: SubscriptionStatus,
    period_end: datetime | None = None,
) -> None:
    uow = SqlAlchemyUnitOfWork(factory)
    async with uow:
        sid = await _session_id(factory)
        await uow.subscriptions.save(
            Subscription(
                sid,
                status=status,
                plan_id="four_week",
                source="demo",
                current_period_start=NOW,
                current_period_end=period_end or NOW + timedelta(days=28),
                auto_renew_consent_at=NOW,
            )
        )
        await uow.commit()


@pytest.mark.parametrize(
    ("status", "with_plan", "period_offset_days", "expected", "reason"),
    [
        (None, False, 0, 402, "no_plan"),
        (None, True, 0, 402, "no_subscription"),
        ("active", True, 10, 200, None),
        ("demo", True, 10, 200, None),
        ("past_due", True, 10, 402, "past_due"),
        ("canceling", True, 10, 200, None),
        ("canceling", True, -1, 402, "no_subscription"),
        ("canceled", True, 10, 402, "no_subscription"),
        ("ended", True, 10, 402, "ended"),
    ],
)
async def test_gate_matrix(
    pclient: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    status: SubscriptionStatus | None,
    with_plan: bool,
    period_offset_days: int,
    expected: int,
    reason: str | None,
) -> None:
    if with_plan:
        await _answer_and_complete(pclient)
    if status is not None:
        await _force_status(session_factory, status, NOW + timedelta(days=period_offset_days))
    r = await pclient.get("/api/_test/gated")
    assert r.status_code == expected, r.text
    if reason:
        error = r.json()["error"]
        assert error["code"] == "payment_required"
        assert error["details"] == {"reason": reason}


async def test_gate_without_token_is_401(pclient: httpx.AsyncClient) -> None:
    r = await pclient.get("/api/_test/gated", headers={"X-Session-Token": "nope"})
    assert r.status_code == 401


async def test_billing_pricing_and_exit_routes_not_gated_when_past_due(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _answer_and_complete(pclient)
    await _force_status(session_factory, "past_due")
    assert (await pclient.get("/api/_test/gated")).status_code == 402
    assert (await pclient.get("/api/_test/open")).status_code == 200
    assert (await pclient.get("/api/pricing")).status_code == 200
    r = await pclient.get("/api/billing/subscription")
    assert r.status_code == 200 and r.json()["status"] == "past_due"
    assert (await pclient.get("/api/resources/crisis")).status_code == 200


async def test_subscription_status_is_none_before_subscribing(pclient: httpx.AsyncClient) -> None:
    body = (await pclient.get("/api/billing/subscription")).json()
    assert body["status"] == "none" and body["planId"] is None


async def test_demo_subscribe_without_consent_returns_422_and_status_unchanged(
    pclient: httpx.AsyncClient,
) -> None:
    await _answer_and_complete(pclient)
    for body in ({"autoRenewConsent": False}, {}):
        r = await pclient.post("/api/billing/demo", json=body)
        assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    r = await pclient.post("/api/billing/demo", json={"autoRenewConsent": False})
    assert r.json()["error"]["code"] == "consent_required"
    assert (await pclient.get("/api/billing/subscription")).json()["status"] == "none"
    assert (await pclient.get("/api/_test/gated")).status_code == 402


async def test_demo_subscribe_without_plan_returns_402_no_plan(pclient: httpx.AsyncClient) -> None:
    r = await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 402
    assert r.json()["error"]["details"] == {"reason": "no_plan"}


async def test_demo_subscribe_unknown_plan_returns_422(pclient: httpx.AsyncClient) -> None:
    await _answer_and_complete(pclient)
    r = await pclient.post("/api/billing/demo", json={"autoRenewConsent": True, "planId": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "unknown_plan"


async def test_demo_subscribe_then_gate_opens_and_history_is_recorded(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _answer_and_complete(pclient)
    r = await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "demo" and body["planId"] == "four_week"
    assert body["autoRenewConsentAt"] is not None and body["renewalCount"] == 0
    assert (await pclient.get("/api/_test/gated")).status_code == 200
    async with session_factory() as db:
        rows = (
            await db.execute(
                text("SELECT from_status, to_status, source FROM subscription_history")
            )
        ).all()
    assert [tuple(row) for row in rows] == [("none", "demo", "demo")]


async def test_second_demo_subscribe_returns_409(pclient: httpx.AsyncClient) -> None:
    await _answer_and_complete(pclient)
    assert (
        await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    ).status_code == 200
    r = await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "already_subscribed"


@pytest.mark.parametrize("status", ["active", "canceling", "past_due"])
async def test_demo_subscribe_with_existing_stripe_subscription_returns_409(
    pclient: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    status: SubscriptionStatus,
) -> None:
    await _answer_and_complete(pclient)
    await _force_status(session_factory, status)
    r = await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_subscribed"


async def test_start_creates_schedule_and_purges_q3_q5_and_locks_quiz(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _answer_and_complete(pclient)
    preview = (await pclient.get("/api/plan/preview")).json()
    async with session_factory() as db:
        before = (await db.execute(text("SELECT answers, tags, branch FROM quiz_states"))).one()
    assert "q3_situation" in before.answers and "q5_changes" in before.answers
    assert (
        await pclient.post("/api/billing/demo", json={"autoRenewConsent": True})
    ).status_code == 200
    async with session_factory() as db:
        quiz = (
            await db.execute(
                text(
                    "SELECT answers, tags, branch, locked, health_answers_purged_at "
                    "FROM quiz_states"
                )
            )
        ).one()
        schedule = (
            await db.execute(text("SELECT lesson_id FROM lesson_schedule ORDER BY seq"))
        ).all()
    assert "q3_situation" not in quiz.answers and "q5_changes" not in quiz.answers
    assert "q6_living" in quiz.answers
    assert (quiz.tags, quiz.branch) == (before.tags, before.branch)
    assert quiz.locked and quiz.health_answers_purged_at is not None
    built = [lesson["id"] for m in preview["modules"] for lesson in m["lessons"] if lesson["built"]]
    assert [row[0] for row in schedule] == built
    assert (await pclient.get("/api/plan/preview")).json() == preview
    r = await pclient.put("/api/quiz/answers/q6_living", json={"value": "far"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "quiz_locked"
    r = await pclient.put("/api/quiz/answers/q3_situation", json={"value": "recent"})
    assert r.status_code == 409


async def test_pricing_first_renewal_date_is_app_today_plus_intro_days(
    pclient: httpx.AsyncClient,
) -> None:
    body = (await pclient.get("/api/pricing")).json()
    assert body["defaultPlanId"] == "four_week"
    plans = {p["id"]: p for p in body["plans"]}
    assert plans["four_week"]["priceToday"] == 19.99
    assert plans["four_week"]["renewalPrice"] == 39.99
    assert plans["four_week"]["firstRenewalDate"] == "2026-02-02"  # 2026-01-05 + 28
    assert plans["twelve_week"]["firstRenewalDate"] == "2026-03-30"  # + 84


async def test_pricing_contains_no_per_day_field(pclient: httpx.AsyncClient) -> None:
    raw: Any = (await pclient.get("/api/pricing")).text.lower()
    assert "perday" not in raw and "per_day" not in raw and "daily" not in raw
    assert "/day" not in raw and "a day" not in raw


async def test_pricing_without_session_returns_plans_and_null_renewal_date_and_writes_no_row(
    db_client: httpx.AsyncClient,
    content: Any,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    r = await db_client.get("/api/pricing")
    assert r.status_code == 200
    body = r.json()
    plans = {p["id"]: p for p in body["plans"]}
    assert plans["four_week"]["priceToday"] == 19.99
    assert plans["four_week"]["renewalPrice"] == 39.99
    assert set(plans) == {p.id for p in content.pricing().plans}
    assert all(p["firstRenewalDate"] is None for p in body["plans"])
    raw = r.text.lower()
    assert "perday" not in raw and "per_day" not in raw and "/day" not in raw
    async with session_factory() as db:
        assert await db.scalar(text("SELECT count(*) FROM sessions")) == 0


async def test_pricing_with_unknown_session_token_is_401(
    db_client: httpx.AsyncClient, content: Any
) -> None:
    r = await db_client.get("/api/pricing", headers={"X-Session-Token": "nope"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_session_token"
