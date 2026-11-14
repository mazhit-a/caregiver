from datetime import timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.fakes.clock import FixedClock
from tests.presentation.test_lessons_api import _answer, pclient, subscribe  # noqa: F401

RATINGS = {"repeat": 3, "accusations": 2, "evenings": 4, "refusal": 1, "visits": 5}


async def test_plan_wrap_and_complete_end_to_end(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "in_person")
    await _answer(pclient, "s6_fifth_time", "slow")

    r = await _answer(pclient, "s8_plan", {"response": "I've got it.", "reminderDownloaded": True})
    assert r.status_code == 200, r.text
    reminder = r.json()["result"]["reminder"]
    assert reminder["startsAt"].startswith("2026-01-05T19:00:00")  # session tz America/New_York
    assert reminder["startsAt"].endswith("-05:00")
    assert reminder["url"] == "http://localhost:3000/lessons/m1_l1"

    r = await _answer(pclient, "s9_wrap", RATINGS)
    assert r.status_code == 200 and r.json()["result"]["saved"] is True

    r = await pclient.post("/api/lessons/m1_l1/complete")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lessonId"] == "m1_l1" and body["doneAt"]
    assert body["wrap"]["skillLine"].startswith("New skill")
    assert body["nextLesson"]["id"] == "m1_l2"
    assert body["nextLesson"]["reason"] and body["nextLesson"]["unlockOn"] > "2026-01-05"
    assert body["allDoneLine"] is None
    again = await pclient.post("/api/lessons/m1_l1/complete")
    assert again.json()["doneAt"] == body["doneAt"]

    async with session_factory() as db:
        plan = (await db.execute(text("SELECT cue, response, reset FROM if_then_plans"))).one()
        task = (await db.execute(text("SELECT text, action, reminder_downloaded FROM tasks"))).one()
        conf = (await db.execute(text("SELECT day0, first, latest FROM confidence"))).one()
        done = (await db.execute(text("SELECT done_at FROM lesson_progress"))).scalar_one()
    assert tuple(plan) == (
        "If Mom asks the same question again,",
        "I've got it.",
        "Say the first words slowly",
    )
    assert tuple(task)[1:] == ("print_note_template", True)
    assert conf.first == RATINGS and conf.latest is None and conf.day0 is not None
    assert done is not None


async def test_plan_response_over_limit_422(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "phone")
    r = await _answer(pclient, "s8_plan", {"response": "x" * 301})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_screen_answer"
    assert r.json()["error"]["details"]["reason"] == "response_too_long"


async def test_slider_out_of_range_422_over_http(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "phone")
    r = await _answer(pclient, "s9_wrap", {**RATINGS, "repeat": 6})
    assert r.status_code == 422
    assert r.json()["error"]["details"]["reason"] == "rating_out_of_range"


async def test_complete_locked_lesson_423(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.post("/api/lessons/m1_l2/complete")
    assert r.status_code == 423 and r.json()["error"]["code"] == "lesson_locked"


async def test_complete_requires_subscription_and_last_built_lesson_is_all_done(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    assert (await pclient.post("/api/lessons/m1_l1/complete")).status_code == 402
    await subscribe(pclient)
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=10))
    r = await pclient.post("/api/lessons/m1_l2/complete")
    assert r.status_code == 200
    assert r.json()["nextLesson"] is None and "More are on the way" in r.json()["allDoneLine"]
