from datetime import timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.fakes.clock import FixedClock
from tests.presentation.test_lessons_api import _answer, pclient, subscribe  # noqa: F401


async def make_plan(client: httpx.AsyncClient) -> None:
    await subscribe(client)
    await _answer(client, "setup", "in_person")
    r = await _answer(client, "plan", {"response": "I point to the note."})
    assert r.status_code == 200, r.text


async def test_checkin_over_http_helped_with_observation_and_recap(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await make_plan(pclient)
    body = {"planId": "m1_l1", "cameUp": "yes", "outcome": "helped"}
    r = await pclient.post("/api/checkins", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "checkin_not_due"
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=1))
    r = await pclient.post(
        "/api/checkins", json={**body, "doctorNote": {"addToVisitSheet": True, "text": "At dinner"}}
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["outcome"] == "helped" and out["taskDone"] and out["observationAdded"]
    assert out["plan"]["response"] == "I point to the note." and out["followUps"] == []
    assert "{recipient}" not in r.text and "{object}" not in r.text
    assert (await pclient.post("/api/checkins", json=body)).status_code == 409
    async with session_factory() as db:
        done = (await db.execute(text("SELECT done_at FROM tasks"))).scalar_one()
        obs = (await db.execute(text("SELECT text, add_to_visit_sheet FROM observations"))).one()
    assert done is not None and tuple(obs) == ("At dinner", True)
    clock.advance(timedelta(days=10))
    recap = (await pclient.get("/api/lessons/m1_l2")).json()["recap"]
    assert recap["text"].endswith(
        "You said it helped. Today we'll make every conversation a little easier."
    )


async def test_didnt_help_over_http_returns_followups(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await make_plan(pclient)
    db_app.state.clock.advance(timedelta(days=1))
    r = await pclient.post(
        "/api/checkins", json={"planId": "m1_l1", "cameUp": "yes", "outcome": "didnt_help"}
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["followUps"]) == 3 and not r.json()["taskDone"]


async def test_invalid_outcome_422(pclient: httpx.AsyncClient, db_app: FastAPI) -> None:  # noqa: F811
    await make_plan(pclient)
    db_app.state.clock.advance(timedelta(days=1))
    r = await pclient.post(
        "/api/checkins", json={"planId": "m1_l1", "cameUp": "yes", "outcome": "great"}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = await pclient.post("/api/checkins", json={"planId": "m1_l1", "cameUp": "yes"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_checkin_answer"
    r = await pclient.post("/api/checkins", json={"planId": "m1_l1", "cameUp": "maybe"})
    assert r.status_code == 422


async def test_unknown_plan_404_over_http(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.post("/api/checkins", json={"planId": "m9_l9", "cameUp": "yes"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "checkin_plan_not_found"


async def test_checkin_requires_subscription_402(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    r = await pclient.post("/api/checkins", json={"planId": "m1_l1", "cameUp": "yes"})
    assert r.status_code == 402
