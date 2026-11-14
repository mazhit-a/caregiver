"""END-TO-END TESTS (TASK.md 13.3). Read this first.

What lives here
- `test_full_journey.py` (this file): the demo-mode journey, the privacy sweep and gentle exit.
- `test_stripe_journey.py`: the Stripe path with signed FakeStripe webhooks.
- `test_roleplay_fallback_real_adapter.py`: the 12 s role-play deadline through the REAL Anthropic
  adapter. Marked `slow` (real wall clock, a few seconds each): excluded from the default run.

What is real: `create_app` with the real Postgres (schema from Alembic), the real `content/`, every
router, use case, repository and the gate. What is faked: only the Coach (`FakeCoach`) and the
PaymentGateway (`FakePaymentGateway`); Stripe webhooks are signed payloads from `FakeStripe`.

Time: the base clock is a `FixedClock` (Monday 2026-01-05 09:00 UTC) in `app.state.clock`; "days
later" is the app's own demo control (`POST /api/demo/next-day`, `/api/demo/jump-to-renewal`, which
move the session's clock offset) and, to go past a period end, advancing the base clock. No sleeps.

Run: `uv run pytest tests/e2e` (default run, slow tests excluded), `uv run pytest -m slow` (the
real-time role-play deadline tests, acceptance run).
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.journey import (
    REPLY_MARKER,
    answer,
    answer_quiz_persona_b,
    base_clock,
    minutes,
    ok,
    play_roleplay,
    walk_variant_free_lesson,
)
from tests.presentation.test_exit_journey_api import (
    EXPECTED_TABLES,
    _row_counts,
    _session_tables,
)

START = date(2026, 1, 5)
RATINGS = {"repeat": 3, "accusations": 2, "evenings": 4, "refusal": 1, "visits": 5}
SAVED_PHRASE = "I'm here. Want some tea?"
LATER_PHRASE = "No rush. Take my arm?"
PLAN_RESPONSE = "I point to the note and say: you're safe, I'm here."
Q_KEYS = ("q3_situation", "q5_changes")


@dataclass
class Journey:
    session_id: Any
    card_id: str


async def _next_day(client: httpx.AsyncClient, expected_today: date) -> None:
    state = await ok(await client.post("/api/demo/next-day"))
    assert state["appToday"] == str(expected_today)


async def _lesson_states(client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    plan = await ok(await client.get("/api/plan"))
    lessons = {x["id"]: x for m in plan["modules"] for x in m["lessons"]}
    assert plan["lessonsPerWeek"] == 4
    return lessons


async def run_demo_journey(
    client: httpx.AsyncClient,
    app: FastAPI,
    factory: async_sessionmaker[AsyncSession],
) -> Journey:
    clock = base_clock(app)

    # --- quiz (persona B), complete, preview and gift ---------------------------------------------
    assert await answer_quiz_persona_b(client)
    preview = await ok(await client.get("/api/plan/preview"))
    assert preview["modules"][0]["id"] == "m1_talking"
    gift = await ok(await client.get("/api/plan/gift"))
    assert gift
    assert (await client.get("/api/lessons/m1_l1")).status_code == 402  # not subscribed yet

    # --- demo subscribe (consent is required) -----------------------------------------------------
    no_consent = await client.post("/api/billing/demo", json={"autoRenewConsent": False})
    assert no_consent.status_code == 422, no_consent.text
    sub = await ok(await client.post("/api/billing/demo", json={"autoRenewConsent": True}))
    assert sub["status"] == "demo" and sub["source"] == "demo" and sub["renewalCount"] == 0
    lessons = await _lesson_states(client)
    assert lessons["m1_l1"]["status"] == "available"
    assert [lessons[f"m1_l{n}"]["unlockOn"] for n in range(1, 6)] == [
        str(START + timedelta(days=d)) for d in (0, 2, 4, 6, 7)
    ]

    # --- lesson 1: variant, scenario, learn mini-tasks, role-play, phrase, plan, wrap -------------
    first = await ok(await client.get("/api/lessons/m1_l1"))
    assert [s["type"] for s in first["screens"]] == ["setup_question"] and first["variant"] is None
    await answer(client, "m1_l1", "s1_setup", "phone")
    lesson = await ok(await client.get("/api/lessons/m1_l1"))
    assert lesson["variant"] == "phone"
    assert [s["type"] for s in lesson["screens"]][:2] == ["setup_question", "scenario"]
    scenario = await answer(client, "m1_l1", "s2_scenario", "a3")
    assert scenario["result"]["feedback"]
    for screen in lesson["screens"]:
        if screen["type"] == "learn" and screen.get("miniTask"):
            task = screen["miniTask"]["options"][0]["id"]
            mini = await answer(client, "m1_l1", screen["id"], task)
            assert mini["result"]["optionId"] == task
    await _roleplay_three_turns(client, app)
    phrase = await ok(
        await client.post(
            "/api/phrases",
            json={"text": SAVED_PHRASE, "source": "roleplay", "lessonId": "m1_l1"},
        ),
        201,
    )
    assert phrase["text"] == SAVED_PHRASE
    plan = await answer(
        client,
        "m1_l1",
        "s8_plan",
        {"response": PLAN_RESPONSE, "reminderDownloaded": True},
    )
    reminder = plan["result"]["reminder"]
    assert reminder["startsAt"].startswith("2026-01-05T") and reminder["url"].endswith("/m1_l1")
    assert reminder["title"] and reminder["timezone"]
    wrap = await answer(client, "m1_l1", "s9_wrap", RATINGS)
    assert wrap["result"]["saved"] is True
    done = await ok(await client.post("/api/lessons/m1_l1/complete"))
    assert done["lessonId"] == "m1_l1" and done["nextLesson"]["id"] == "m1_l2"
    assert done["nextLesson"]["unlockOn"] == str(START + timedelta(days=2))
    assert (await client.get("/api/lessons/m1_l2")).status_code == 423

    # --- next day: Today shows the check-in and the practice round --------------------------------
    today = await ok(await client.get("/api/today"))
    assert today["checkIn"] is None and today["practiceRound"] is None
    await _next_day(client, START + timedelta(days=1))
    today = await ok(await client.get("/api/today"))
    assert today["order"][:2] == ["checkIn", "practiceRound"]
    assert today["checkIn"]["plan"]["response"] == PLAN_RESPONSE
    assert today["practiceRound"]["context"] == "practice_round"
    assert today["practiceRound"]["variant"] == "phone"
    assert (await client.get("/api/lessons/m1_l2")).status_code == 423  # day 2 not yet
    checkin = await ok(
        await client.post(
            "/api/checkins",
            json={
                "planId": "m1_l1",
                "cameUp": "yes",
                "outcome": "helped",
                "doctorNote": {"addToVisitSheet": True, "text": "At dinner"},
            },
        )
    )
    assert checkin["outcome"] == "helped" and checkin["taskDone"] and checkin["observationAdded"]
    today = await ok(await client.get("/api/today"))
    assert today["checkIn"] is None and today["practiceRound"] is not None

    # --- care card published, then a new phrase: Today nudges to update it ------------------------
    await ok(await client.put("/api/profile", json={"displayName": "Margaret", "calms": ["tea"]}))
    card = await ok(await client.post("/api/care-card", json={}))
    card_id = card["link"].rstrip("/").rsplit("/", 1)[-1]
    assert (await ok(await client.get("/api/today")))["careCardNudge"] is None
    clock.advance(minutes(5))
    saved = await ok(
        await client.post("/api/phrases", json={"text": LATER_PHRASE, "source": "scenario"}), 201
    )
    assert saved["text"] == LATER_PHRASE
    today = await ok(await client.get("/api/today"))
    assert today["careCardNudge"]["newPhraseCount"] == 1
    assert "careCardNudge" in today["order"]

    # --- lessons 2 to 5 unlock on days 2, 4, 6, 7 and are walked through --------------------------
    for lesson_id, day in (("m1_l2", 2), ("m1_l3", 4), ("m1_l4", 6), ("m1_l5", 7)):
        while (await ok(await client.get("/api/demo")))["appToday"] != str(
            START + timedelta(days=day)
        ):
            locked = await client.get(f"/api/lessons/{lesson_id}")
            assert locked.status_code == 423, (lesson_id, locked.text)
            assert locked.json()["error"]["details"]["unlockOn"] == str(START + timedelta(days=day))
            await _next_day(
                client,
                date.fromisoformat((await ok(await client.get("/api/demo")))["appToday"])
                + timedelta(days=1),
            )
        states = await _lesson_states(client)
        assert states[lesson_id]["status"] == "available"
        done = await walk_variant_free_lesson(client, lesson_id, app)
        assert done["wrap"]
    assert done["nextLesson"] is None and "More are on the way" in done["allDoneLine"]
    today = await ok(await client.get("/api/today"))
    assert today["nextStep"]["kind"] == "all_done"

    # --- jump to renewal: renewal_count = 1, then profile, visit sheet and skills reads -----------
    before = await ok(await client.get("/api/demo"))
    jumped = await ok(await client.post("/api/demo/jump-to-renewal"))
    assert jumped["appNow"] > before["currentPeriodEnd"]  # the app clock is past the period end
    sub = await ok(await client.get("/api/billing/subscription"))  # the demo renewal rolls lazily
    assert sub["status"] == "demo" and sub["renewalCount"] == 1
    assert sub["currentPeriodStart"] == before["currentPeriodEnd"]
    assert (await ok(await client.get("/api/demo")))["renewalCount"] == 1
    profile = await ok(await client.get("/api/profile"))
    assert profile["displayName"] == "Margaret" and profile["calms"] == ["tea"]
    saved_sheet = await ok(
        await client.put("/api/visit-sheet", json={"familyNotes": "Slept badly"})
    )
    assert saved_sheet["familyNotes"] == "Slept badly"
    visit = await ok(await client.get("/api/visit-sheet"))
    assert visit["familyNotes"] == "Slept badly"
    assert any("At dinner" in n["text"] for n in visit["suggestedNotes"]), visit
    skills = await ok(await client.get("/api/skills"))
    assert skills["confidence"]["first"] == RATINGS
    assert skills["counts"]["phrasesSaved"] == 2 and skills["counts"]["tasksHelped"] >= 1
    talking = next(x for x in skills["skills"] if x["roleplay"] and x["roleplay"]["runs"] >= 1)
    assert talking["roleplay"]["latestScore"] == 3

    # --- cancel: canceling keeps access, after the period end the gate says 402 -------------------
    preview_cancel = await ok(await client.get("/api/billing/cancel-preview"))
    assert preview_cancel["savedPhraseCount"] == 2 and preview_cancel["careCardPublished"]
    canceled = await ok(await client.post("/api/billing/cancel"))
    assert canceled["status"] == "canceling"
    assert (await client.get("/api/lessons/m1_l1")).status_code == 200
    period_end = canceled["endDate"]
    assert period_end
    clock.advance(timedelta(days=60))  # past the period end of the (offset) app clock
    ended = await client.get("/api/lessons/m1_l1")
    assert ended.status_code == 402, ended.text
    assert ended.json()["error"]["details"] == {"reason": "no_subscription"}
    assert (await ok(await client.get("/api/billing/subscription")))["status"] == "canceled"

    async with factory() as db:
        sid = (await db.execute(text("SELECT id FROM sessions"))).scalar_one()
    return Journey(session_id=sid, card_id=card_id)


async def _roleplay_three_turns(client: httpx.AsyncClient, app: FastAPI) -> None:
    result = await play_roleplay(client, "m1_l1", turns=3)
    assert result["scores"] == [3, 3, 3]


async def test_full_journey_demo_path(
    e2e_app: FastAPI,
    learner: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await run_demo_journey(learner, e2e_app, session_factory)


async def _all_rows_text(factory: async_sessionmaker[AsyncSession]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    async with factory() as db:
        tables = (
            await db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        ).scalars()
        for table in list(tables):
            rows = (await db.execute(text(f'SELECT t::text FROM "{table}" t'))).scalars().all()  # noqa: S608
            out[table] = list(rows)
    return out


async def test_no_roleplay_text_and_no_q3_q5_raw_answers_in_db_or_logs_after_journey(
    e2e_app: FastAPI,
    learner: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    await run_demo_journey(learner, e2e_app, session_factory)
    tables = await _all_rows_text(session_factory)
    assert tables["roleplay_runs"], "the journey must have stored role-play runs"
    for table, rows in tables.items():
        for row in rows:
            assert REPLY_MARKER not in row, table
            assert "You sound worried" not in row, table
            assert not any(key in row for key in Q_KEYS), (table, row[:200])
    logged = "\n".join(f"{r.name} {r.getMessage()}" for r in caplog.records)
    assert logged, "log capture is not working"
    assert REPLY_MARKER not in logged and "You sound worried" not in logged
    # The question id is in the URL path (`/api/quiz/answers/q3_situation`); the answers are not.
    for raw in ('"value"', "repeats", "evenings", '"recent"', '["repeats"'):
        assert raw not in logged, raw
    assert learner.headers["X-Session-Token"] not in logged


async def test_gentle_exit_after_journey_leaves_no_rows(
    e2e_app: FastAPI,
    learner: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    journey = await run_demo_journey(learner, e2e_app, session_factory)
    tables = await _session_tables(session_factory)
    assert tables >= EXPECTED_TABLES - {"events"}  # the cascade helper's table list is the truth
    before = await _row_counts(session_factory, tables, journey.session_id)
    empty = sorted(t for t, count in before.items() if count < 1 and t != "events")
    assert not empty, empty  # the journey filled every session table

    r = await ok(await learner.post("/api/exit/gentle"))
    assert r["title"] and r["condolence"] and r["resources"]

    after = await _row_counts(session_factory, tables, journey.session_id)
    assert after == dict.fromkeys(after, 0), after
    learner.headers.pop("X-Session-Token")
    assert (await learner.get(f"/api/cards/{journey.card_id}")).status_code == 404
