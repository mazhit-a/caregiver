import re
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.presentation.api.deps import AppInfo
from tests.fakes.clock import FixedClock
from tests.fakes.roleplay import FakeCoach
from tests.presentation.test_checkins_api import make_plan
from tests.presentation.test_lessons_api import _answer, pclient, subscribe  # noqa: F401
from tests.presentation.test_roleplay_api import REPLY

TOP_ORDER = ["checkIn", "practiceRound", "careCardNudge", "nextStep", "weeklyRhythm", "readiness"]


async def get_today(client: httpx.AsyncClient) -> dict[str, object]:
    r = await client.get("/api/today")
    assert r.status_code == 200, r.text
    assert not re.search(r"\{[A-Za-z_]\w*\}", r.text)
    body: dict[str, object] = r.json()
    return body


async def finish_run(client: httpx.AsyncClient, context: str) -> None:
    r = await client.post("/api/roleplay/start", json={"lessonId": "m1_l1", "context": context})
    assert r.status_code == 200, r.text
    run_id = r.json()["runId"]
    r = await client.post(f"/api/roleplay/{run_id}/turn", json={"round": 1, "reply": REPLY})
    assert r.status_code == 200, r.text
    phrases = {"phrases": [{"reply": REPLY, "betterPhrase": "Better."}]}
    r = await client.post(f"/api/roleplay/{run_id}/finish", json=phrases)
    assert r.status_code == 200, r.text


async def test_today_requires_subscription_402(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    r = await pclient.get("/api/today")
    assert r.status_code == 402 and r.json()["error"]["details"] == {"reason": "no_plan"}


async def test_today_returns_402_past_due_when_payment_failed(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await subscribe(pclient)
    assert (await pclient.get("/api/today")).status_code == 200
    async with session_factory() as db:
        await db.execute(text("UPDATE subscriptions SET status = 'past_due'"))
        await db.commit()
    r = await pclient.get("/api/today")
    assert r.status_code == 402 and r.json()["error"]["details"] == {"reason": "past_due"}


async def test_today_day_0_hero_is_lesson_1_and_no_checkin(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await make_plan(pclient)  # the plan exists, but it was made today
    body = await get_today(pclient)
    assert body["checkIn"] is None and body["practiceRound"] is None
    step = body["nextStep"]
    assert isinstance(step, dict) and step["kind"] == "lesson"
    assert step["lesson"]["lessonId"] == "m1_l1" and step["lesson"]["reason"]
    assert step["lesson"]["minutes"] > 0
    assert body["visitSheetLink"] == {
        "label": "Prepare for a doctor visit",
        "path": "/api/visit-sheet",
    }
    assert body["order"][:2] == ["nextStep", "weeklyRhythm"]
    assert body["welcomeBack"] is None


async def test_today_next_day_has_checkin_quoting_users_plan_then_practice_round_then_next_lesson(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await make_plan(pclient)
    db_app.state.clock.advance(timedelta(days=1))
    body = await get_today(pclient)
    order = body["order"]
    assert isinstance(order, list)
    assert [name for name in order if name in TOP_ORDER] == [
        "checkIn",
        "practiceRound",
        "nextStep",
        "weeklyRhythm",
        "readiness",
    ]
    keys = list(body)
    assert keys.index("checkIn") < keys.index("practiceRound") < keys.index("nextStep")
    check_in = body["checkIn"]
    assert isinstance(check_in, dict) and check_in["planId"] == "m1_l1"
    assert check_in["plan"]["response"] == "I point to the note."
    assert check_in["question"] and [o["id"] for o in check_in["options"]] == ["yes", "not_yet"]
    assert check_in["followUp"]["ifAnswer"] == "yes"
    round_ = body["practiceRound"]
    assert isinstance(round_, dict) and round_["context"] == "practice_round"
    assert isinstance(body["nextStep"], dict) and body["nextStep"]["kind"] == "lesson"


async def test_today_checkin_disappears_after_answer(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await make_plan(pclient)
    db_app.state.clock.advance(timedelta(days=1))
    assert (await get_today(pclient))["checkIn"] is not None
    r = await pclient.post(
        "/api/checkins", json={"planId": "m1_l1", "cameUp": "yes", "outcome": "partly"}
    )
    assert r.status_code == 200, r.text
    body = await get_today(pclient)
    assert body["checkIn"] is None
    assert isinstance(body["practiceRound"], dict)  # offered after the check-in either way


async def test_today_practice_round_is_day2_practice_round_for_the_stored_variant(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    await subscribe(pclient)
    await _answer(pclient, "s1_setup", "phone")
    await _answer(pclient, "s8_plan", {"response": "I point to the note."})
    db_app.state.clock.advance(timedelta(days=1))
    day2 = db_app.state.content.render_lesson(
        "m1_l1",
        "mom",
        "phone",
        runtime_values={"savedPhrase": "", "firstScore": "", "lastScore": ""},
    )["day2"]["practiceRound"]
    round_ = (await get_today(pclient))["practiceRound"]
    assert isinstance(round_, dict)
    assert round_["variant"] == "phone" and round_["title"] == day2["title"]
    assert round_["roundsTotal"] == len(day2["roundsByVariant"]["phone"])
    started = await pclient.post(
        "/api/roleplay/start", json={"lessonId": "m1_l1", "context": "practice_round"}
    )
    assert started.json()["rounds"][0]["line"] == day2["roundsByVariant"]["phone"][0]["line"]


async def test_care_card_nudge_appears_after_new_phrase_saved_after_publish_and_not_before(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    clock: FixedClock = db_app.state.clock
    await subscribe(pclient)
    assert (await get_today(pclient))["careCardNudge"] is None  # no card yet
    saved = {"text": "I am here.", "source": "scenario"}
    assert (await pclient.post("/api/phrases", json=saved)).status_code in (200, 201)
    clock.advance(timedelta(minutes=5))
    assert (await pclient.post("/api/care-card", json={})).status_code == 200
    assert (await get_today(pclient))["careCardNudge"] is None  # saved before the publish
    clock.advance(timedelta(minutes=5))
    saved = {"text": "One more.", "source": "scenario"}
    assert (await pclient.post("/api/phrases", json=saved)).status_code in (200, 201)
    nudge = (await get_today(pclient))["careCardNudge"]
    assert nudge == {
        "newPhraseCount": 1,
        "text": "Your care card has 1 new phrase. Update it?",
    }
    body = await get_today(pclient)
    assert isinstance(body["order"], list) and "careCardNudge" in body["order"]


async def test_weekly_rhythm_counts_finished_runs_of_both_contexts_this_week_only(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    clock: FixedClock = db_app.state.clock
    await make_plan(pclient)  # Monday 2026-01-05 09:00 UTC
    await finish_run(pclient, "lesson")
    clock.advance(timedelta(days=1))
    await finish_run(pclient, "practice_round")
    await pclient.post("/api/roleplay/start", json={"lessonId": "m1_l1", "context": "lesson"})
    rhythm = (await get_today(pclient))["weeklyRhythm"]
    assert isinstance(rhythm, dict)
    assert rhythm["done"] == 2  # the unfinished run is not counted
    plan = (await pclient.get("/api/plan")).json()
    assert rhythm["target"] == plan["lessonsPerWeek"]
    assert rhythm["text"] == f"This week: 2 of {plan['lessonsPerWeek']} practice sessions."
    clock.set(datetime(2026, 1, 12, 15, 0, tzinfo=UTC))  # next Monday
    rhythm = (await get_today(pclient))["weeklyRhythm"]
    assert isinstance(rhythm, dict) and rhythm["done"] == 0


async def test_weekly_rhythm_uses_monday_to_sunday_in_session_timezone_over_http(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    clock: FixedClock = db_app.state.clock
    await make_plan(pclient)
    clock.set(datetime(2026, 1, 12, 3, 0, tzinfo=UTC))  # Sunday 22:00 in New York
    await finish_run(pclient, "lesson")
    assert (await get_today(pclient))["weeklyRhythm"]["done"] == 1  # type: ignore[index]
    clock.set(datetime(2026, 1, 12, 6, 0, tzinfo=UTC))  # Monday 01:00 in New York: a new week
    assert (await get_today(pclient))["weeklyRhythm"]["done"] == 0  # type: ignore[index]


async def test_subscription_notice_variants_renews_on_then_renewed(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    notice = (await get_today(pclient))["subscriptionNotice"]
    assert isinstance(notice, dict) and notice["kind"] == "renews_on"
    assert notice["text"].startswith("Your plan renews on ") and notice["on"]
    assert (await pclient.post("/api/demo/jump-to-renewal")).status_code == 200
    renewed = (await get_today(pclient))["subscriptionNotice"]
    assert isinstance(renewed, dict) and renewed["kind"] == "renewed"
    assert renewed["text"].startswith("Your plan renewed on ")


async def test_welcome_back_after_7_days_only(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    clock: FixedClock = db_app.state.clock
    await subscribe(pclient)
    assert (await get_today(pclient))["welcomeBack"] is None  # a request at app time T
    clock.advance(timedelta(days=6))  # no request in between
    assert (await get_today(pclient))["welcomeBack"] is None
    clock.advance(timedelta(days=6, hours=23))  # 6 d 23 h since the last request
    assert (await get_today(pclient))["welcomeBack"] is None
    clock.advance(timedelta(days=7))
    welcome = (await get_today(pclient))["welcomeBack"]
    assert welcome == {
        "title": "Welcome back",
        "body": "Pick up whenever you're ready. One short step is plenty.",
    }
    assert (await get_today(pclient))["welcomeBack"] is None  # the visit just now reset it


async def test_welcome_back_shows_at_exactly_7_days_after_a_request(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    await get_today(pclient)
    db_app.state.clock.advance(timedelta(days=7))
    assert (await get_today(pclient))["welcomeBack"] is not None


async def test_demo_block_hidden_when_demo_controls_false(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    db_app.state.app_info = AppInfo(demo_controls=True)
    shown = (await get_today(pclient))["demo"]
    assert isinstance(shown, dict) and shown["clockOffsetSeconds"] == 0
    assert [c["id"] for c in shown["controls"]] == ["nextDay", "jumpToRenewal"]
    assert shown["appToday"] == "2026-01-05"
    db_app.state.app_info = AppInfo(demo_controls=False)
    body = await get_today(pclient)
    assert body["demo"] is None and "demo" not in body["order"]  # type: ignore[operator]
