"""Lessons 2 to 5 of the REAL content, end to end through the API with a fake coach."""

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
    client: httpx.AsyncClient, lesson_id: str, db_app: FastAPI, coach_down: bool = False
) -> dict[str, Any]:
    """Open the lesson and answer every screen the way a learner would."""
    r = await client.get(f"/api/lessons/{lesson_id}")
    assert r.status_code == 200, r.text
    lesson = r.json()
    assert lesson["variant"] is None
    assert lesson["screens"][0]["type"] != "setup_question"  # no setup question: all screens shown
    db_app.state.coach = (
        FakeCoach(*[unavailable() for _ in range(3)]) if coach_down else FakeCoach()
    )
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
            saved["roleplay"] = await play(client, lesson_id, screen, coach_down)
        elif kind == "plan":
            res = await _answer(client, screen["id"], PLAN_ANSWER, lesson_id)
            assert res.status_code == 200, res.text
            assert res.json()["result"]["ifThen"]["response"] == PLAN_ANSWER["response"]
            saved["reset"] = res.json()["result"]["ifThen"]["reset"]
    done = await client.post(f"/api/lessons/{lesson_id}/complete")
    assert done.status_code == 200, done.text
    saved["complete"] = done.json()
    return saved


async def play(
    client: httpx.AsyncClient, lesson_id: str, screen: dict[str, Any], coach_down: bool = False
) -> dict[str, Any]:
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
        if coach_down:  # the lesson's own multiple-choice scenario for this round takes over
            assert turn.json()["mode"] == "fallback"
            scenarios = turn.json()["fallbackScenarios"]
            assert (
                scenarios and scenarios[number - 1]["line"] == screen["rounds"][number - 1]["line"]
            )
            continue  # a fallback turn has no score, so nothing to send back at the end
        phrases.append({"reply": reply, "betterPhrase": turn.json()["coach"]["betterPhrase"]})
    fin = await client.post(f"/api/roleplay/{run['runId']}/finish", json={"phrases": phrases})
    assert fin.status_code == 200, fin.text
    body: dict[str, Any] = fin.json()
    assert body["scores"] == ([] if coach_down else [3, 3, 3])
    return body


async def test_five_built_lessons_unlock_on_days_0_2_4_6_7_with_4_per_week(
    rclient: httpx.AsyncClient,
) -> None:
    body = (await rclient.get("/api/plan")).json()
    lessons = lessons_by_id(body)
    start = date.fromisoformat("2026-01-05")
    assert body["lessonsPerWeek"] == 4
    assert lessons["m1_l1"]["status"] == "available"
    assert lessons["m1_l1"]["unlockOn"] == str(start)
    for lesson_id, offset in {"m1_l2": 2, "m1_l3": 4, "m1_l4": 6, "m1_l5": 7}.items():
        assert lessons[lesson_id]["status"] == "locked", lesson_id
        assert lessons[lesson_id]["unlockOn"] == str(start + timedelta(days=offset)), lesson_id


async def test_plan_shows_no_coming_later_for_module_1_lessons(
    rclient: httpx.AsyncClient,
) -> None:
    body = (await rclient.get("/api/plan")).json()
    module_1 = next(m for m in body["modules"] if m["id"] == "m1_talking")
    assert [lesson["id"] for lesson in module_1["lessons"]] == [f"m1_l{n}" for n in range(1, 6)]
    assert all(lesson["status"] != "coming_later" for lesson in module_1["lessons"])


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
    assert three["complete"]["nextLesson"]["id"] == "m1_l4"
    assert three["complete"]["allDoneLine"] is None
    assert "When Mom says no" in three["complete"]["wrap"]["nextLine"]


async def test_lessons_4_and_5_walkthrough_with_fake_coach_and_recap(
    rclient: httpx.AsyncClient, db_app: FastAPI
) -> None:
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=7))
    await rclient.post(
        "/api/phrases",
        json={"text": "I'm here. Tea first?", "source": "scenario", "lessonId": "m1_l3"},
    )
    await walk_through(rclient, "m1_l3", db_app)
    four = await walk_through(rclient, "m1_l4", db_app)
    assert four["complete"]["nextLesson"]["id"] == "m1_l5"
    assert four["reset"]
    five = await walk_through(rclient, "m1_l5", db_app)
    assert five["complete"]["nextLesson"] is None
    assert "More are on the way" in five["complete"]["allDoneLine"]
    assert five["reset"]


async def test_lesson_5_lists_saved_phrases_and_shows_empty_state_when_none(
    rclient: httpx.AsyncClient, db_app: FastAPI
) -> None:
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=7))

    def review(lesson: dict[str, Any]) -> dict[str, Any]:
        found: dict[str, Any] = next(s for s in lesson["screens"] if s["type"] == "phrases_review")
        return found

    empty = review((await rclient.get("/api/lessons/m1_l5")).json())
    assert empty["phrases"] == [] and empty["emptyText"] and empty["title"]

    for text, lesson_id in [("I'm here. Tea?", "m1_l1"), ("Blue top or green top?", "m1_l4")]:
        r = await rclient.post(
            "/api/phrases", json={"text": text, "source": "scenario", "lessonId": lesson_id}
        )
        assert r.status_code in (200, 201), r.text
        clock.advance(timedelta(minutes=1))  # saved_at orders the phrases
    filled = review((await rclient.get("/api/lessons/m1_l5")).json())
    assert [p["text"] for p in filled["phrases"]] == ["I'm here. Tea?", "Blue top or green top?"]
    assert [p["lessonId"] for p in filled["phrases"]] == ["m1_l1", "m1_l4"]
    assert all(p["id"] and p["source"] == "scenario" for p in filled["phrases"])


async def test_review_screen_takes_no_answer(rclient: httpx.AsyncClient, db_app: FastAPI) -> None:
    db_app.state.clock.advance(timedelta(days=7))
    r = await _answer(rclient, "s2_phrases", "x", "m1_l5")
    assert r.status_code == 422


async def test_all_five_lessons_walkthrough_completes_with_fallback_only_coach(
    rclient: httpx.AsyncClient, db_app: FastAPI
) -> None:
    """The coach is unavailable for every turn; every lesson still completes."""
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=10))
    for lesson_id in ("m1_l2", "m1_l3", "m1_l4", "m1_l5"):
        done = await walk_through(rclient, lesson_id, db_app, coach_down=True)
        assert done["complete"]["lessonId"] == lesson_id
    # Lesson 1 asks its setup question first, so only its role-play is checked here.
    await _answer(rclient, "s1_setup", "in_person", "m1_l1")
    db_app.state.coach = FakeCoach(*[unavailable() for _ in range(3)])
    run = (await rclient.post("/api/roleplay/start", json={"lessonId": "m1_l1"})).json()
    for number in (1, 2, 3):
        r = await rclient.post(
            f"/api/roleplay/{run['runId']}/turn",
            json={"round": number, "reply": "You sound worried. I'm here."},
        )
        assert r.status_code == 200 and r.json()["mode"] == "fallback", r.text
