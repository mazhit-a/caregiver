from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.content.provider import JsonContentProvider
from app.presentation.api.deps import AppInfo, SubscribedSession
from tests.fakes.clock import FixedClock
from tests.presentation.test_billing_api import NOW, _answer_and_complete, _force_status
from tests.presentation.test_plan_api import REPO

_probe = APIRouter(prefix="/_demo_test")


@_probe.get("/gated")
async def _gated(session: SubscribedSession) -> dict[str, str]:
    return {"ok": "gated"}


@pytest.fixture
async def dclient(
    db_app: FastAPI, db_client: httpx.AsyncClient
) -> AsyncIterator[httpx.AsyncClient]:
    db_app.state.content = JsonContentProvider.from_directory(REPO / "content")
    db_app.include_router(_probe, prefix="/api")
    response = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = response.json()["token"]
    yield db_client


async def _subscribe(client: httpx.AsyncClient) -> None:
    await _answer_and_complete(client)
    r = await client.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 200, r.text


async def test_next_day_moves_app_today_by_one_day(dclient: httpx.AsyncClient) -> None:
    before = (await dclient.get("/api/demo")).json()
    after = (await dclient.post("/api/demo/next-day")).json()
    assert before["clockOffsetSeconds"] == 0
    assert after["clockOffsetSeconds"] == 86400
    assert before["appToday"] == "2026-01-05" and after["appToday"] == "2026-01-06"
    assert (await dclient.get("/api/demo")).json()["appToday"] == "2026-01-06"


async def test_demo_controls_disabled_returns_404_error_shape(
    db_app: FastAPI, dclient: httpx.AsyncClient
) -> None:
    db_app.state.app_info = AppInfo(demo_controls=False)
    for method, path in (
        ("GET", "/api/demo"),
        ("POST", "/api/demo/next-day"),
        ("POST", "/api/demo/jump-to-renewal"),
    ):
        r = await dclient.request(method, path)
        assert r.status_code == 404
        error = r.json()["error"]
        assert error["code"] == "not_found" and error["details"] == {}
        assert isinstance(error["message"], str)


async def test_demo_response_is_labelled_demo(dclient: httpx.AsyncClient) -> None:
    for r in (await dclient.get("/api/demo"), await dclient.post("/api/demo/next-day")):
        body = r.json()
        assert body["demoControls"] is True
        assert "demo" in body["label"].lower()


async def test_jump_to_renewal_then_read_rolls_period_and_renewal_count_is_1(
    dclient: httpx.AsyncClient,
) -> None:
    await _subscribe(dclient)
    first = (await dclient.get("/api/billing/subscription")).json()
    jumped = (await dclient.post("/api/demo/jump-to-renewal")).json()
    assert jumped["appNow"] > first["currentPeriodEnd"]
    read = (await dclient.get("/api/billing/subscription")).json()
    assert read["status"] == "demo" and read["renewalCount"] == 1
    assert read["currentPeriodStart"] == first["currentPeriodEnd"]
    assert read["currentPeriodEnd"] > jumped["appNow"]
    assert (await dclient.get("/api/_demo_test/gated")).status_code == 200


async def test_jumping_twice_gives_renewal_count_2(dclient: httpx.AsyncClient) -> None:
    await _subscribe(dclient)
    await dclient.post("/api/demo/jump-to-renewal")
    assert (await dclient.get("/api/billing/subscription")).json()["renewalCount"] == 1
    await dclient.post("/api/demo/jump-to-renewal")
    assert (await dclient.get("/api/billing/subscription")).json()["renewalCount"] == 2


async def test_jump_without_subscription_returns_409(dclient: httpx.AsyncClient) -> None:
    r = await dclient.post("/api/demo/jump-to-renewal")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "no_subscription_period"


async def test_demo_renewal_records_history_with_app_time(
    dclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _subscribe(dclient)
    period_end = (await dclient.get("/api/billing/subscription")).json()["currentPeriodEnd"]
    await dclient.post("/api/demo/jump-to-renewal")
    await dclient.get("/api/billing/subscription")
    async with session_factory() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT from_status, to_status, event, source, at FROM subscription_history"
                    " ORDER BY at"
                )
            )
        ).all()
    assert [tuple(r)[:4] for r in rows] == [
        ("none", "demo", "started", "demo"),
        ("demo", "demo", "demo_renewed", "demo"),
    ]
    # The renewal is stamped with the app time of the period boundary, not the wall clock.
    assert rows[1].at.isoformat().replace("+00:00", "Z") == period_end.replace("+00:00", "Z")
    assert rows[1].at == NOW + timedelta(days=28)


async def test_canceling_demo_subscription_becomes_canceled_at_period_end_and_gate_returns_402_no_subscription(  # noqa: E501
    db_app: FastAPI,
    dclient: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(db_app.state.clock, FixedClock)
    await _answer_and_complete(dclient)
    await _force_status(session_factory, "canceling")
    assert (await dclient.get("/api/_demo_test/gated")).status_code == 200
    await dclient.post("/api/demo/jump-to-renewal")
    sub = (await dclient.get("/api/billing/subscription")).json()
    assert sub["status"] == "canceled" and sub["renewalCount"] == 0
    r = await dclient.get("/api/_demo_test/gated")
    assert r.status_code == 402
    assert r.json()["error"]["details"] == {"reason": "no_subscription"}
