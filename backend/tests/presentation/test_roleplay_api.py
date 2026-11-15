import logging
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.roleplay.lesson_source import render, rounds_for
from app.domain.roleplay.run import RunContext
from app.domain.session.entities import Session
from app.infrastructure.config import Settings
from app.infrastructure.llm.factory import build_coach
from app.infrastructure.rate_limit import InMemoryRateLimiter
from tests.fakes.roleplay import FakeCoach, unavailable
from tests.presentation.test_lessons_api import _answer, pclient, subscribe  # noqa: F401

REPLY = "You sound worried about tomorrow. I'm here and I'll handle it. Want some tea?"
CRISIS_REPLY = "Sometimes I think about how I want to kill myself, this is too much."
SECRET = "zebra-quartz-7731"


async def start(
    client: httpx.AsyncClient, variant: str = "phone", context: str = "lesson"
) -> dict[str, object]:
    await _answer(client, "setup", variant)
    r = await client.post("/api/roleplay/start", json={"lessonId": "m1_l1", "context": context})
    assert r.status_code == 200, r.text
    body: dict[str, object] = r.json()
    return body


async def turn(
    client: httpx.AsyncClient,
    run_id: object,
    reply: str = REPLY,
    round_: int = 1,
    extra: dict[str, object] | None = None,
) -> httpx.Response:
    body: dict[str, object] = {"round": round_, "reply": reply, **(extra or {})}
    return await client.post(f"/api/roleplay/{run_id}/turn", json=body)


@pytest.mark.parametrize("variant", ["in_person", "phone"])
async def test_start_returns_round_1_line_by_variant(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    variant: str,
) -> None:
    await subscribe(pclient)
    body = await start(pclient, variant)
    lesson = render(db_app.state.content, _session(), "m1_l1", variant)
    expected = rounds_for(lesson, RunContext.LESSON, variant)
    rounds = body["rounds"]
    assert isinstance(rounds, list)
    assert rounds[0]["line"] == expected[0].line and rounds[0]["stage"] == expected[0].stage
    assert body["variant"] == variant and body["roundsTotal"] == len(expected)
    assert body["runId"] and body["goals"] and body["context"] == "lesson"


def _session() -> Session:
    now = datetime(2026, 1, 5, tzinfo=UTC)
    return Session(uuid4(), "h", "UTC", timedelta(), now, now, recipient_key="mom")


async def test_turn_returns_coach_panel_and_labelled_ai_text(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    await subscribe(pclient)
    run = await start(pclient)
    r = await turn(pclient, run["runId"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "ai" and body["round"] == 1
    coach = body["coach"]
    assert coach["aiGenerated"] is True and coach["score"] == 3
    assert coach["goals"] == {"notice": True, "reassure": True, "offer": True}
    assert coach["betterPhrase"] and coach["parentReaction"] and coach["tip"]
    assert body["fallbackScenarios"] == [] and body["resources"] == []


async def test_turn_with_crisis_text_returns_safety_mode_and_postgres_has_no_reply_text(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    coach = FakeCoach()
    db_app.state.coach = coach
    await subscribe(pclient)
    run = await start(pclient)
    ok = await turn(pclient, run["runId"], f"{REPLY} {SECRET}")
    assert ok.status_code == 200
    r = await turn(pclient, run["runId"], f"{CRISIS_REPLY} {SECRET}", round_=2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "safety" and body["kind"] == "crisis" and body["resources"]
    assert body["coach"] is None
    assert len(coach.calls) == 1  # the crisis reply never reached the coach
    async with session_factory() as db:
        tables = (
            await db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        ).scalars()
        for table in list(tables):
            rows = (await db.execute(text(f'SELECT t::text FROM "{table}" t'))).scalars().all()  # noqa: S608
            assert not any(SECRET in row or "kill myself" in row for row in rows), table
        assert (await db.execute(text("SELECT count(*) FROM roleplay_runs"))).scalar_one() == 1


async def test_turn_429_returns_friendly_message_in_error_shape(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    db_app.state.rate_limiter = InMemoryRateLimiter(1)
    await subscribe(pclient)
    run = await start(pclient)
    assert (await turn(pclient, run["runId"])).status_code == 200
    r = await turn(pclient, run["runId"], round_=2)
    assert r.status_code == 429
    error = r.json()["error"]
    assert error["code"] == "rate_limited" and "quick choices" in error["message"]
    assert error["details"] == {}


@pytest.mark.parametrize("reply", ["", "x" * 151])
async def test_turn_422_for_empty_and_over_150_reply(
    pclient: httpx.AsyncClient,  # noqa: F811
    reply: str,
) -> None:
    await subscribe(pclient)
    run = await start(pclient)
    r = await turn(pclient, run["runId"], reply)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert "x" * 50 not in r.text


async def test_whitespace_only_reply_is_422_invalid_reply(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    run = await start(pclient)
    r = await turn(pclient, run["runId"], "   ")
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_reply"


async def test_turn_on_other_sessions_run_404(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    await subscribe(pclient)
    run = await start(pclient)
    transport = httpx.ASGITransport(app=db_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as other:
        token = (await other.post("/api/session")).json()["token"]
        other.headers["X-Session-Token"] = token
        await subscribe(other)
        r = await turn(other, run["runId"])
        assert r.status_code == 404 and r.json()["error"]["code"] == "run_not_found"
        r = await other.post(f"/api/roleplay/{run['runId']}/finish", json={"phrases": []})
        assert r.status_code == 404
    assert (await turn(pclient, uuid4())).status_code == 404


async def test_fallback_response_contains_lesson_fallbackScenarios(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    # No API key: the real adapter is built without a client and raises CoachUnavailable.
    db_app.state.coach = build_coach(Settings(_env_file=None, anthropic_api_key=""))
    await subscribe(pclient)
    run = await start(pclient)
    r = await turn(pclient, run["runId"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "fallback" and body["runMode"] == "fallback"
    assert [s["id"] for s in body["fallbackScenarios"]] == ["fb1", "fb2"]
    assert body["coach"] is None
    assert not re.search(r"\{[A-Za-z]+\}", r.text)


async def test_roleplay_endpoints_require_subscription_gate(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    for path, body in (
        ("/api/roleplay/start", {"lessonId": "m1_l1"}),
        (f"/api/roleplay/{uuid4()}/turn", {"round": 1, "reply": "hi"}),
        (f"/api/roleplay/{uuid4()}/finish", {"phrases": []}),
    ):
        r = await pclient.post(path, json=body)
        assert r.status_code == 402, path
        assert r.json()["error"]["details"] == {"reason": "no_plan"}


async def test_finish_returns_summary_best_phrase_and_run_is_over(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    await subscribe(pclient)
    run = await start(pclient)
    assert (await turn(pclient, run["runId"])).status_code == 200
    r = await pclient.post(f"/api/roleplay/{run['runId']}/finish", json={"phrases": []})
    assert r.status_code == 422 and r.json()["error"]["code"] == "turns_mismatch"
    phrases = {"phrases": [{"reply": REPLY, "betterPhrase": "Better."}]}
    r = await pclient.post(f"/api/roleplay/{run['runId']}/finish", json=phrases)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scores"] == [3] and body["bestPhrase"] == REPLY
    assert body["summary"]["firstScore"] == 3 and body["firstVsLast"]
    again = await turn(pclient, run["runId"], round_=2)
    assert again.status_code == 409 and again.json()["error"]["code"] == "run_finished"


async def test_round_mismatch_is_422(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    await subscribe(pclient)
    run = await start(pclient)
    r = await turn(pclient, run["runId"], round_=2)
    assert r.status_code == 422 and r.json()["error"]["code"] == "round_mismatch"


async def test_roleplay_request_fields_over_limit_return_422_error_shape(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    coach = FakeCoach()
    db_app.state.coach = coach
    await subscribe(pclient)
    run = await start(pclient)
    good = {"parent": "p", "caregiver": "c", "score": 1}
    bad_bodies: list[dict[str, object]] = [
        {"previousTurns": [good] * 4},
        {"previousTurns": [{**good, "caregiver": "x" * 151}]},
        {"previousTurns": [{**good, "parent": "x" * 401}]},
        {"previousTurns": [{**good, "score": 4}]},
        {"round": 0},
    ]
    for extra in bad_bodies:
        r = await turn(pclient, run["runId"], extra=extra)
        assert r.status_code == 422, extra
        assert r.json()["error"]["code"] == "validation_error"
        assert "xxxxxxxxxx" not in r.text
    r = await pclient.post("/api/roleplay/not-a-uuid/turn", json={"round": 1, "reply": "hi"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = await pclient.post("/api/roleplay/not-a-uuid/finish", json={})
    assert r.status_code == 422
    too_long = {"phrases": [{"reply": "x" * 501, "betterPhrase": "b"}]}
    r = await pclient.post(f"/api/roleplay/{run['runId']}/finish", json=too_long)
    assert r.status_code == 422
    too_long = {"phrases": [{"reply": "r", "betterPhrase": "b" * 401}]}
    r = await pclient.post(f"/api/roleplay/{run['runId']}/finish", json=too_long)
    assert r.status_code == 422
    r = await pclient.post("/api/roleplay/start", json={"lessonId": "x" * 65})
    assert r.status_code == 422
    assert coach.calls == []


async def test_access_log_and_app_log_have_no_request_body(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db_app.state.coach = FakeCoach(unavailable(), unavailable())
    await subscribe(pclient)
    run = await start(pclient)
    caplog.set_level(logging.DEBUG)
    reply = f"{REPLY} {SECRET}"
    await turn(pclient, run["runId"], reply)
    await turn(pclient, run["runId"], f"{CRISIS_REPLY} {SECRET}", round_=1)
    await pclient.post(
        f"/api/roleplay/{run['runId']}/finish",
        json={"phrases": [{"reply": f"{SECRET}-finish", "betterPhrase": f"{SECRET}-bp"}]},
    )
    await turn(pclient, run["runId"], "", round_=1)  # a 422 must not echo or log the body either
    assert any(r.name == "app.request" for r in caplog.records)
    for record in caplog.records:
        assert SECRET not in record.getMessage()
        assert "kill myself" not in record.getMessage()


async def test_app_wires_one_limiter_per_process_and_the_hourly_cap_from_settings(
    app: FastAPI, settings: Settings
) -> None:
    from app.application.roleplay.limiter import LlmConcurrencyLimiter

    assert isinstance(app.state.llm_limiter, LlmConcurrencyLimiter)
    assert isinstance(app.state.rate_limiter, InMemoryRateLimiter)
    assert app.state.settings.llm_timeout_seconds == settings.llm_timeout_seconds
