"""Response shapes of the new lesson screen types (P10), on a temp lesson 1 built from
`tests/lesson_content_v2.py`: camelCase, nothing server-only, 422 shapes, the gate."""

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.infrastructure.content.provider import JsonContentProvider
from tests.lesson_content_v2 import make_v2_content_dir
from tests.presentation.test_lessons_api import _answer, subscribe


@pytest.fixture
async def vclient(
    db_app: FastAPI, db_client: httpx.AsyncClient, tmp_path: Path
) -> AsyncIterator[httpx.AsyncClient]:
    db_app.state.content = JsonContentProvider.from_directory(
        make_v2_content_dir(tmp_path / "content")
    )
    response = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = response.json()["token"]
    await subscribe(db_client)
    yield db_client


async def _full_lesson(client: httpx.AsyncClient) -> dict[str, object]:
    assert (await _answer(client, "setup", "phone")).status_code == 200
    r = await client.get("/api/lessons/m1_l1")
    assert r.status_code == 200, r.text
    body: dict[str, object] = r.json()
    return body


def _screen(lesson: dict[str, object], kind: str) -> dict[str, object]:
    screens = lesson["screens"]
    assert isinstance(screens, list)
    return next(s for s in screens if s["type"] == kind)


async def test_before_the_setup_answer_two_screens_but_the_full_screen_count(
    vclient: httpx.AsyncClient,
) -> None:
    body = (await vclient.get("/api/lessons/m1_l1")).json()
    assert [s["type"] for s in body["screens"]] == ["intro", "setup"]
    assert body["screenCount"] == 10
    intro, setup = body["screens"]
    assert set(intro) == {"id", "type", "part", "title", "body", "bullets", "image"}
    assert set(setup) == {"id", "type", "part", "title", "body", "options"}
    assert setup["options"][0] == {"id": "in_person", "label": "In person"}


async def test_every_new_screen_type_has_its_exact_camel_case_shape(
    vclient: httpx.AsyncClient,
) -> None:
    lesson = await _full_lesson(vclient)
    assert lesson["screenCount"] == len(lesson["screens"]) == 10  # type: ignore[arg-type]
    scenario = _screen(lesson, "scenario")
    assert set(scenario) == {
        "id",
        "type",
        "part",
        "title",
        "intro",
        "note",
        "setup",
        "line",
        "answers",
    }
    assert scenario["answers"] == [{"id": "a1", "text": "Say who you are."}]
    content = _screen(lesson, "content")
    assert content["body"] == ["Listen to Mom."]
    assert set(content) == {
        "id",
        "type",
        "part",
        "title",
        "body",
        "image",
        "items",
        "steps",
        "dodont",
        "examples",
        "note",
        "keyIdea",
        "tip",
    }
    assert content["items"] == [{"title": "One", "text": "Notice"}]
    quiz = _screen(lesson, "quiz")
    assert quiz["options"] == [
        {"id": "o1", "text": "Argue about facts"},
        {"id": "o2", "text": "Name the feeling"},
    ]
    builder = _screen(lesson, "builder")
    groups = builder["groups"]
    assert isinstance(groups, list)
    assert [g["id"] for g in groups] == ["g1", "g2"]
    assert set(groups[0]) == {"id", "label", "options"}
    assert set(groups[0]["options"][0]) == {"id", "text"}
    reset = _screen(lesson, "reset")
    assert reset["options"] == [
        {"id": "r1", "label": "One slow breath"},
        {"id": "r2", "label": "Step away"},
    ]
    wrap = _screen(lesson, "wrap")
    assert wrap["title"] == "Well done" and wrap["learned"] == ["Notice the feeling"]


async def test_no_screen_leaks_correctness_verdicts_or_feedback(
    vclient: httpx.AsyncClient,
) -> None:
    await _full_lesson(vclient)
    raw = (await vclient.get("/api/lessons/m1_l1")).text
    for forbidden in (
        '"correct"',
        '"verdict"',
        '"feedback"',
        '"savePhrase"',
        '"planText"',
        '"verdictLabels"',
        '"afterChoice"',
        '"sec"',
        '"minutes":8,"title":"Talking',
    ):
        assert forbidden not in raw


async def test_answer_results_for_the_new_screens(vclient: httpx.AsyncClient) -> None:
    await _full_lesson(vclient)
    quiz = (await _answer(vclient, "check", "o1")).json()
    assert quiz["type"] == "quiz"
    assert quiz["result"]["correct"] is False and quiz["result"]["correctOptionId"] == "o2"
    builder = (await _answer(vclient, "build", ["o1", "o1"])).json()
    assert builder["result"]["allCorrect"] is True and builder["result"]["groups"] == [
        {"correct": True},
        {"correct": True},
    ]
    reset = (await _answer(vclient, "you", "r1")).json()
    assert reset["result"] == {"optionId": "r1", "text": "take one slow breath"}


async def test_answer_rejections_are_422_with_the_shared_error_shape(
    vclient: httpx.AsyncClient,
) -> None:
    await _full_lesson(vclient)
    for screen_id, value in (("check", "o9"), ("build", ["o1"]), ("you", 3), ("idea", "x")):
        r = await _answer(vclient, screen_id, value)
        assert r.status_code == 422, (screen_id, r.text)
        assert set(r.json()["error"]) == {"code", "message", "details"}


async def test_lesson_routes_stay_behind_the_gate(
    db_app: FastAPI, db_client: httpx.AsyncClient, tmp_path: Path
) -> None:
    db_app.state.content = JsonContentProvider.from_directory(
        make_v2_content_dir(tmp_path / "content")
    )
    response = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = response.json()["token"]
    assert (await db_client.get("/api/lessons/m1_l1")).status_code == 402
    assert (await _answer(db_client, "setup", "phone")).status_code == 402


def test_openapi_builds_with_the_new_screen_types(db_app: FastAPI) -> None:
    schemas = db_app.openapi()["components"]["schemas"]
    for name in (
        "IntroScreenOut",
        "SetupScreenOut",
        "ContentScreenOut",
        "QuizScreenOut",
        "BuilderScreenOut",
        "ResetScreenOut",
        "LessonCopyOut",
    ):
        assert name in schemas
    assert "screenCount" in schemas["LessonResponse"]["properties"]
