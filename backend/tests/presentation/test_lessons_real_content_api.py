"""Lessons 2 and 3 of the REAL content, end to end through the API with a fake coach."""

from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.infrastructure.content.provider import JsonContentProvider
from tests.fakes.clock import FixedClock
from tests.fakes.roleplay import FakeCoach, unavailable
from tests.lesson_content import REPO
from tests.presentation.test_lessons_api import _answer, subscribe
from tests.presentation.test_phrases_plan_api import lessons_by_id

PLAN_ANSWER = {"response": "You sound worried. I'm here. Want to look together?"}


@pytest.fixture
async def rclient(db_app: FastAPI, db_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """The real `content/` directory (not the fixture copy), a subscribed session."""
    db_app.state.content = JsonContentProvider.from_directory(REPO / "content")
    r = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = r.json()["token"]
    await subscribe(db_client)
    return db_client


async def walk_through(
    client: httpx.AsyncClient, lesson_id: str, db_app: FastAPI
) -> dict[str, Any]:
    """Open the lesson and answer every screen the way a learner would."""
    r = await client.get(f"/api/lessons/{lesson_id}")
    assert r.status_code == 200, r.text
    lesson = r.json()
    assert lesson["variant"] is None
    assert lesson["screens"][0]["type"] != "setup_question"  # no setup question: all screens shown
    db_app.state.coach = FakeCoach()
    saved: dict[str, Any] = {}
    for screen in lesson["screens"]:
        kind = screen["type"]
        if kind == "scenario":
            for answer in screen["answers"]:
                res = await _answer(client, screen["id"], answer["id"], lesson_id)
                assert res.status_code == 200, res.text
                assert res.json()["result"]["feedback"]
                if res.json()["result"]["savePhrase"]:
                    saved["phrase"] = answer["text"]
        elif kind == "learn" and screen.get("miniTask"):
            for option in screen["miniTask"]["options"]:
                res = await _answer(client, screen["id"], option["id"], lesson_id)
                assert res.status_code == 200, res.text
                assert res.json()["result"]["response"] is not None or screen["id"].endswith(
                    "reset"
                )
        elif kind == "roleplay":
            saved["roleplay"] = await play(client, lesson_id, screen)
        elif kind == "plan":
            res = await _answer(client, screen["id"], PLAN_ANSWER, lesson_id)
            assert res.status_code == 200, res.text
            assert res.json()["result"]["ifThen"]["response"] == PLAN_ANSWER["response"]
            saved["reset"] = res.json()["result"]["ifThen"]["reset"]
    done = await client.post(f"/api/lessons/{lesson_id}/complete")
    assert done.status_code == 200, done.text
    saved["complete"] = done.json()
    return saved


async def play(client: httpx.AsyncClient, lesson_id: str, screen: dict[str, Any]) -> dict[str, Any]:
    r = await client.post("/api/roleplay/start", json={"lessonId": lesson_id, "context": "lesson"})
    assert r.status_code == 200, r.text
    run = r.json()
    assert run["variant"] is None and run["roundsTotal"] == len(screen["rounds"]) == 3
    phrases = []
    for number in range(1, run["roundsTotal"] + 1):
        reply = f"You sound unsure about round {number}. I'm here. Want to sit with me?"
        turn = await client.post(
            f"/api/roleplay/{run['runId']}/turn", json={"round": number, "reply": reply}
        )
        assert turn.status_code == 200, turn.text
        phrases.append({"reply": reply, "betterPhrase": turn.json()["coach"]["betterPhrase"]})
    fin = await client.post(f"/api/roleplay/{run['runId']}/finish", json={"phrases": phrases})
    assert fin.status_code == 200, fin.text
    body: dict[str, Any] = fin.json()
    assert body["scores"] == [3, 3, 3]
    return body


async def test_plan_after_marking_built_schedules_lessons_2_and_3(
    rclient: httpx.AsyncClient,
) -> None:
    lessons = lessons_by_id((await rclient.get("/api/plan")).json())
    start = date.fromisoformat("2026-01-05")
    assert lessons["m1_l1"]["status"] == "available"
    for lesson_id, offset in {"m1_l2": 2, "m1_l3": 4}.items():  # 4 a week: days 0, 2, 4
        assert lessons[lesson_id]["status"] == "locked", lesson_id
        assert lessons[lesson_id]["unlockOn"] == str(start + timedelta(days=offset)), lesson_id
    assert lessons["m1_l4"]["status"] == "coming_later"


async def test_lesson_2_and_3_walkthrough_with_fake_coach_and_recaps(
    rclient: httpx.AsyncClient, db_app: FastAPI
) -> None:
    clock: FixedClock = db_app.state.clock
    # Lesson 1's saved phrase must appear in lesson 2's recap.
    await rclient.post(
        "/api/phrases", json={"text": "I'm here. Tea?", "source": "roleplay", "lessonId": "m1_l1"}
    )
    clock.advance(timedelta(days=2))
    recap = (await rclient.get("/api/lessons/m1_l2")).json()["recap"]
    assert recap["fromLessonId"] == "m1_l1"
    assert 'Your phrase was: "I\'m here. Tea?"' in recap["text"]

    two = await walk_through(rclient, "m1_l2", db_app)
    assert two["complete"]["nextLesson"] is None or two["complete"]["nextLesson"]["id"] == "m1_l3"
    assert two["reset"]  # the reset the learner picked is stored with the plan
    assert two["complete"]["wrap"]["nextLine"]

    # Lesson 2's saved phrase appears in lesson 3's recap.
    await rclient.post(
        "/api/phrases",
        json={"text": "No rush. Take my arm?", "source": "scenario", "lessonId": "m1_l2"},
    )
    clock.advance(timedelta(days=2))
    recap = (await rclient.get("/api/lessons/m1_l3")).json()["recap"]
    assert recap["fromLessonId"] == "m1_l2"
    assert 'Your phrase was: "No rush. Take my arm?"' in recap["text"]
    assert "talking so it lands" in recap["text"]

    three = await walk_through(rclient, "m1_l3", db_app)
    assert three["complete"]["nextLesson"] is None
    assert "More are on the way" in three["complete"]["allDoneLine"]


async def test_lessons_2_and_3_complete_with_a_coach_that_is_always_unavailable(
    rclient: httpx.AsyncClient, db_app: FastAPI
) -> None:
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=10))
    for lesson_id in ("m1_l2", "m1_l3"):
        db_app.state.coach = FakeCoach(*[unavailable() for _ in range(3)])
        lesson = (await rclient.get(f"/api/lessons/{lesson_id}")).json()
        run = (await rclient.post("/api/roleplay/start", json={"lessonId": lesson_id})).json()
        for number in (1, 2, 3):
            r = await rclient.post(
                f"/api/roleplay/{run['runId']}/turn",
                json={"round": number, "reply": "You sound worried. I'm here."},
            )
            assert r.status_code == 200, r.text
            assert r.json()["mode"] == "fallback"
            assert r.json()["fallbackScenarios"], (lesson_id, number)
        assert lesson["screens"]
