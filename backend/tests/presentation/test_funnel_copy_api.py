import re
from datetime import timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.content.provider import JsonContentProvider  # noqa: F401
from tests.fakes.clock import FixedClock
from tests.presentation.test_plan_api import _complete_b, content, pclient  # noqa: F401


def _short(iso: str) -> str:
    _year, month, day = (int(p) for p in iso.split("-"))
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{names[month - 1]} {day}"


async def test_funnel_copy_requires_a_session(db_client: httpx.AsyncClient) -> None:
    r = await db_client.get("/api/funnel-copy")
    assert r.status_code == 401


async def test_funnel_copy_before_the_quiz_is_402_no_plan(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    r = await pclient.get("/api/funnel-copy")
    assert r.status_code == 402 and r.json()["error"]["details"] == {"reason": "no_plan"}


async def test_funnel_copy_is_finished_text_for_the_session(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    assert (await _complete_b(pclient)).status_code == 200
    r = await pclient.get("/api/funnel-copy")
    assert r.status_code == 200, r.text
    assert not re.search(r"\{[A-Za-z_]\w*\}|\*\*", r.text)
    body = r.json()
    assert body["loader"]["title"] == "Building Mom's plan…"
    assert body["planPreview"]["title"] == "Your first 30 days with Mom"
    assert body["planPreview"]["cta"] == "Get Mom's plan"
    assert body["planPreview"]["highlightLabel"] == "For now"
    assert body["quiz"]["healthNote"].startswith("This page has no ad tracking.")
    paywall = body["paywall"]
    plan_preview = (await pclient.get("/api/plan/preview")).json()
    assert paywall["subhead"] == plan_preview["whatWeHeard"][0]
    assert paywall["defaultPlanId"] == "four_week"
    pricing = (await pclient.get("/api/pricing")).json()
    for copy, plan in zip(paywall["plans"], pricing["plans"], strict=True):
        assert copy["id"] == plan["id"]
        assert copy["priceToday"] == f"${plan['priceToday']:.2f}"
        assert f"${plan['renewalPrice']:.2f}" in copy["consentLabel"]
        assert copy["firstRenewalDate"] == _short(plan["firstRenewalDate"])
        assert copy["payButtonLabel"] == f"Pay {copy['priceToday']} and start"


async def test_funnel_copy_renewal_date_follows_the_app_clock(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await _complete_b(pclient)
    before = (await pclient.get("/api/funnel-copy")).json()["paywall"]["plans"][0]
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=3))
    after = (await pclient.get("/api/funnel-copy")).json()["paywall"]["plans"][0]
    assert after["firstRenewalDate"] != before["firstRenewalDate"]
    pricing = (await pclient.get("/api/pricing")).json()["plans"][0]
    assert after["firstRenewalDate"] == _short(pricing["firstRenewalDate"])


async def test_funnel_copy_writes_nothing(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _complete_b(pclient)

    async def snapshot() -> tuple[object, ...]:
        async with session_factory() as db:
            rows = await db.execute(
                text(
                    "SELECT (SELECT count(*) FROM sessions), (SELECT count(*) FROM plans),"
                    " (SELECT count(*) FROM subscriptions)"
                )
            )
            return tuple(rows.one())

    before = await snapshot()
    assert (await pclient.get("/api/funnel-copy")).status_code == 200
    assert await snapshot() == before
