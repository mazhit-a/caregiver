"""END-TO-END: the 24-screen lesson 1 through the real app, real Postgres and real `content/`.

Only the Coach is faked. Covers each screen type once (scenario with a saved phrase, six quizzes
answered right and wrong, builder, reset, role-play, plan with the reset in `ifThen.reset`, wrap),
completion, the next-day check-in, resume, and the privacy sweeps (quiz and role-play text never in
a table; "clear my data" leaves zero rows).
"""

import json
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.journey import REPLY_MARKER, answer, answer_quiz_persona_b, ok, play_roleplay
from tests.presentation.test_exit_journey_api import _row_counts, _session_tables

PLAN_TEXT = "xq-plan-marker I breathe first, then answer."


async def _subscribe(client: httpx.AsyncClient) -> None:
    await answer_quiz_persona_b(client)
    await ok(await client.post("/api/billing/demo", json={"autoRenewConsent": True}))


async def _open_lesson(client: httpx.AsyncClient, variant: str) -> dict[str, Any]:
    first = await ok(await client.get("/api/lessons/m1_l1"))
    assert [s["type"] for s in first["screens"]] == ["intro", "setup"]
    await answer(client, "m1_l1", "setup", variant)
    lesson: dict[str, Any] = await ok(await client.get("/api/lessons/m1_l1"))
    assert lesson["screenCount"] == len(lesson["screens"]) == 24
    return lesson


async def _walk(client: httpx.AsyncClient, lesson: dict[str, Any]) -> dict[str, Any]:
    """Answer all 24 screens: each quiz wrong then right, every scenario answer, builder, reset."""
    seen: dict[str, Any] = {"quizzes": 0, "texts": []}
    for screen in lesson["screens"]:
        kind, sid = screen["type"], screen["id"]
        if kind == "scenario":
            for option in screen["answers"]:
                res = (await answer(client, "m1_l1", sid, option["id"]))["result"]
                assert res["feedback"] and res["verdict"] in ("best", "okay", "try_again")
        elif kind == "quiz":
            seen["quizzes"] += 1
            first = (await answer(client, "m1_l1", sid, screen["options"][0]["id"]))["result"]
            right = first["correctOptionId"]
            wrong = next(o["id"] for o in screen["options"] if o["id"] != right)
            res = (await answer(client, "m1_l1", sid, wrong))["result"]
            assert res["correct"] is False and res["feedback"]
            res = (await answer(client, "m1_l1", sid, right))["result"]
            assert res["correct"] is True and res["feedback"]
            seen["texts"].append(res["feedback"])
        elif kind == "builder":
            picks = [group["options"][0]["id"] for group in screen["groups"]]
            res = (await answer(client, "m1_l1", sid, picks))["result"]
            assert res["reply"]
            seen["texts"].append(res["reply"])
        elif kind == "reset":
            res = (await answer(client, "m1_l1", sid, screen["options"][0]["id"]))["result"]
            seen["reset"] = res["text"]
        elif kind == "roleplay":
            assert (await play_roleplay(client, "m1_l1"))["scores"] == [3, 3, 3]
        elif kind == "plan":
            res = (await answer(client, "m1_l1", sid, {"response": PLAN_TEXT}))["result"]
            assert res["ifThen"]["reset"] == seen["reset"]
            assert res["ifThen"]["response"] == PLAN_TEXT
        elif kind == "wrap":
            ratings = {item["id"]: 4 for item in screen["confidenceCheck"]["items"]}
            assert (await answer(client, "m1_l1", sid, ratings))["result"]["saved"] is True
    assert seen["quizzes"] == 6
    return seen


async def test_lesson_1_journey_completes_and_next_day_check_in_appears(
    e2e_app: FastAPI, learner: httpx.AsyncClient
) -> None:
    await _subscribe(learner)
    lesson = await _open_lesson(learner, "phone")
    await _walk(learner, lesson)
    done = await ok(await learner.post("/api/lessons/m1_l1/complete"))
    assert done["nextLesson"]["id"] == "m1_l2" and done["wrap"]
    today = await ok(await learner.get("/api/today"))
    assert today["checkIn"] is None  # same app day: not yet
    await ok(await learner.post("/api/demo/next-day"))
    assert (await ok(await learner.get("/api/today")))["checkIn"] is not None


async def test_lesson_1_resume_returns_the_saved_step(
    e2e_app: FastAPI, learner: httpx.AsyncClient
) -> None:
    await _subscribe(learner)
    await _open_lesson(learner, "in_person")
    saved = await ok(await learner.put("/api/lessons/m1_l1/progress", json={"step": 23}))
    assert saved["step"] == 23
    again = await ok(await learner.get("/api/lessons/m1_l1"))
    assert again["progress"]["step"] == 23 and again["variant"] == "in_person"


async def test_no_quiz_or_roleplay_text_in_any_table_and_clear_data_leaves_zero_rows(
    e2e_app: FastAPI,
    learner: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _subscribe(learner)
    lesson = await _open_lesson(learner, "both")
    seen = await _walk(learner, lesson)
    await ok(await learner.post("/api/lessons/m1_l1/complete"))
    quiz_texts = list(seen["texts"])
    for screen in lesson["screens"]:
        if screen["type"] == "quiz":
            quiz_texts += [str(o.get("label") or o.get("text") or "") for o in screen["options"]]
    quiz_texts = [t for t in quiz_texts if len(t) >= 20]
    assert len(quiz_texts) >= 6
    async with session_factory() as db:
        names = (
            (await db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")))
            .scalars()
            .all()
        )
        dump = ""
        for table in names:
            rows = (await db.execute(text(f'SELECT t::text FROM "{table}" t'))).scalars().all()  # noqa: S608
            dump += "\n".join(rows)
    assert REPLY_MARKER not in dump and "You sound worried" not in dump
    for fragment in quiz_texts:
        assert json.dumps(fragment)[1:-1] not in dump and fragment not in dump, fragment
    assert "q3_situation" not in dump.replace("alembic", "")

    tables = await _session_tables(session_factory)
    async with session_factory() as db:
        sid = (await db.execute(text("SELECT id FROM sessions"))).scalar_one()
    before = await _row_counts(session_factory, tables, sid)
    assert before["lesson_progress"] and before["if_then_plans"] and before["scenario_answers"]
    assert await ok(await learner.delete("/api/session"))
    after = await _row_counts(session_factory, tables, sid)
    assert after == dict.fromkeys(after, 0), after
