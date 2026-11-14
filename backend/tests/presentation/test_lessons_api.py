from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.content.provider import JsonContentProvider
from tests.fakes.clock import FixedClock
from tests.lesson_content import make_content_dir
from tests.presentation.test_plan_api import PERSONA_B


@pytest.fixture
async def pclient(
    db_app: FastAPI, db_client: httpx.AsyncClient, tmp_path: Path
) -> AsyncIterator[httpx.AsyncClient]:
    db_app.state.content = JsonContentProvider.from_directory(
        make_content_dir(tmp_path / "content")
    )
    response = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = response.json()["token"]
    yield db_client


async def subscribe(client: httpx.AsyncClient) -> None:
    for question, value in PERSONA_B.items():
        r = await client.put(f"/api/quiz/answers/{question}", json={"value": value})
        assert r.status_code == 200, r.text
    assert (await client.post("/api/quiz/complete")).status_code == 200
    r = await client.post("/api/billing/demo", json={"autoRenewConsent": True})
    assert r.status_code == 200, r.text


async def test_lesson_endpoints_require_subscription_gate(pclient: httpx.AsyncClient) -> None:
    r = await pclient.get("/api/lessons/m1_l1")
    assert r.status_code == 402
    assert r.json()["error"]["code"] == "payment_required"
    assert r.json()["error"]["details"] == {"reason": "no_plan"}
    for question, value in PERSONA_B.items():
        await pclient.put(f"/api/quiz/answers/{question}", json={"value": value})
    await pclient.post("/api/quiz/complete")
    r = await pclient.get("/api/lessons/m1_l1")
    assert r.status_code == 402 and r.json()["error"]["details"] == {"reason": "no_subscription"}


async def test_lesson_requires_a_session_token(pclient: httpx.AsyncClient) -> None:
    r = await pclient.get("/api/lessons/m1_l1", headers={"X-Session-Token": "nope"})
    assert r.status_code == 401


async def test_first_lesson_renders_setup_screen_before_the_variant_is_known(
    pclient: httpx.AsyncClient,
) -> None:
    await subscribe(pclient)
    r = await pclient.get("/api/lessons/m1_l1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == "m1_l1" and body["variant"] is None
    assert body["title"] == "When Mom asks again"
    assert [s["type"] for s in body["screens"]] == ["setup_question"]
    assert body["progress"]["step"] == 0 and body["progress"]["doneAt"] is None


async def test_locked_lesson_returns_423_with_unlock_on(pclient: httpx.AsyncClient) -> None:
    await subscribe(pclient)
    r = await pclient.get("/api/lessons/m1_l2")
    assert r.status_code == 423
    error = r.json()["error"]
    assert error["code"] == "lesson_locked"
    assert error["details"]["unlockOn"] > "2026-01-05"
    assert error["details"]["lesson"] == "m1_l2"


async def test_lesson_unlocks_when_the_app_day_arrives(
    pclient: httpx.AsyncClient, db_app: FastAPI
) -> None:
    await subscribe(pclient)
    assert (await pclient.get("/api/lessons/m1_l2")).status_code == 423
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=10))
    r = await pclient.get("/api/lessons/m1_l2")
    assert r.status_code == 200 and r.json()["variant"] is None
    assert len(r.json()["screens"]) == 8


async def test_unknown_lesson_returns_404(pclient: httpx.AsyncClient) -> None:
    await subscribe(pclient)
    r = await pclient.get("/api/lessons/does_not_exist")
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_lesson"


async def test_unbuilt_lesson_returns_404_lesson_not_available(pclient: httpx.AsyncClient) -> None:
    await subscribe(pclient)
    r = await pclient.get("/api/lessons/m1_l3")
    assert r.status_code == 404 and r.json()["error"]["code"] == "lesson_not_available"


async def _set_progress(
    factory: async_sessionmaker[AsyncSession], variant: str | None, step: int
) -> None:
    async with factory() as db:
        await db.execute(
            text("UPDATE lesson_progress SET variant = :v, step = :s WHERE lesson_id = 'm1_l1'"),
            {"v": variant, "s": step},
        )
        await db.commit()


async def test_variant_and_step_from_progress_are_returned_and_scenario_does_not_leak(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await subscribe(pclient)
    await pclient.get("/api/lessons/m1_l1")  # marks started
    await _set_progress(session_factory, "phone", 4)
    r = await pclient.get("/api/lessons/m1_l1")
    body = r.json()
    assert body["variant"] == "phone" and body["progress"]["step"] == 4
    assert len(body["screens"]) == 9
    scenario = next(s for s in body["screens"] if s["type"] == "scenario")
    assert "calls" in scenario["setup"]
    assert [a["id"] for a in scenario["answers"]] == ["a1", "a2", "a3", "a4"]
    raw = r.text
    for forbidden in ('verdict"', "feedback", "savePhrase", '"response"', '"correct"'):
        assert forbidden not in raw.replace("verdictLabels", "")


async def test_scenario_response_does_not_leak_verdicts(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await subscribe(pclient)
    await pclient.get("/api/lessons/m1_l1")
    await _set_progress(session_factory, "in_person", 1)
    body = (await pclient.get("/api/lessons/m1_l1")).json()
    scenario = next(s for s in body["screens"] if s["type"] == "scenario")
    assert set(scenario["answers"][0]) == {"id", "text"}
    assert set(scenario) <= {
        "id",
        "type",
        "intro",
        "setup",
        "line",
        "question",
        "answers",
        "verdictLabels",
        "afterChoice",
        "saveButton",
    }
    for learn in (s for s in body["screens"] if s["type"] == "learn" and s.get("miniTask")):
        assert all(set(o) == {"id", "label"} for o in learn["miniTask"]["options"])
