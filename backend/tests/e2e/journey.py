"""Step helpers shared by the end-to-end tests (no test functions here)."""

from datetime import timedelta
from typing import Any

import httpx
from fastapi import FastAPI

from tests.fakes.clock import FixedClock
from tests.fakes.roleplay import FakeCoach
from tests.presentation.test_plan_api import PERSONA_B

#: Role-play replies carry unique markers so the privacy sweep can look for them everywhere.
REPLY_MARKER = "xq-reply-marker"
Q_KEYS_PURGED = ("q3_situation", "q5_changes")


def reply_text(lesson_id: str, number: int) -> str:
    return f"You sound worried, {REPLY_MARKER}-{lesson_id}-{number}. I'm here. Want to sit with me?"


async def ok(response: httpx.Response, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


async def answer(
    client: httpx.AsyncClient, lesson_id: str, screen_id: str, value: object
) -> dict[str, Any]:
    body: dict[str, Any] = await ok(
        await client.post(
            f"/api/lessons/{lesson_id}/answers", json={"screenId": screen_id, "value": value}
        )
    )
    return body


async def answer_quiz_persona_b(client: httpx.AsyncClient) -> dict[str, Any]:
    for question, value in PERSONA_B.items():
        await ok(await client.put(f"/api/quiz/answers/{question}", json={"value": value}))
    body: dict[str, Any] = await ok(await client.post("/api/quiz/complete"))
    return body


async def play_roleplay(
    client: httpx.AsyncClient, lesson_id: str, turns: int = 3
) -> dict[str, Any]:
    """Start a lesson run, play `turns` rounds and finish it the way the browser does."""
    run = await ok(
        await client.post("/api/roleplay/start", json={"lessonId": lesson_id, "context": "lesson"})
    )
    phrases = []
    for number in range(1, turns + 1):
        reply = reply_text(lesson_id, number)
        turn = await ok(
            await client.post(
                f"/api/roleplay/{run['runId']}/turn", json={"round": number, "reply": reply}
            )
        )
        assert turn["mode"] == "ai"
        phrases.append({"reply": reply, "betterPhrase": turn["coach"]["betterPhrase"]})
    finished: dict[str, Any] = await ok(
        await client.post(f"/api/roleplay/{run['runId']}/finish", json={"phrases": phrases})
    )
    return finished


async def walk_variant_free_lesson(
    client: httpx.AsyncClient, lesson_id: str, app: FastAPI
) -> dict[str, Any]:
    """Open lesson 2 to 5 and answer every screen the way a learner would, then complete it."""
    lesson: dict[str, Any] = await ok(await client.get(f"/api/lessons/{lesson_id}"))
    assert lesson["variant"] is None and lesson["screens"][0]["type"] != "setup_question"
    app.state.coach = FakeCoach()
    kinds = []
    for screen in lesson["screens"]:
        kind = screen["type"]
        kinds.append(kind)
        if kind == "scenario":
            for option in screen["answers"]:
                res = await answer(client, lesson_id, screen["id"], option["id"])
                assert res["result"]["feedback"]
        elif kind == "learn" and screen.get("miniTask"):
            await answer(client, lesson_id, screen["id"], screen["miniTask"]["options"][0]["id"])
        elif kind == "roleplay":
            assert (await play_roleplay(client, lesson_id))["scores"] == [3, 3, 3]
        elif kind == "plan":
            res = await answer(client, lesson_id, screen["id"], {"response": "I stay calm."})
            assert res["result"]["ifThen"]["response"] == "I stay calm."
    assert "roleplay" in kinds and "plan" in kinds
    done: dict[str, Any] = await ok(await client.post(f"/api/lessons/{lesson_id}/complete"))
    assert done["lessonId"] == lesson_id and done["doneAt"]
    return done


def base_clock(app: FastAPI) -> FixedClock:
    clock: FixedClock = app.state.clock
    return clock


def minutes(count: int) -> timedelta:
    return timedelta(minutes=count)
