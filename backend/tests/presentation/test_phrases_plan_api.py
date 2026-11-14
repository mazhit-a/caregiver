import copy
import json
from datetime import date, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI

from app.domain.phrases.entities import MAX_PHRASES_PER_SESSION
from app.infrastructure.content.provider import JsonContentProvider
from tests.fakes.clock import FixedClock
from tests.presentation.test_lessons_api import _answer, pclient, subscribe  # noqa: F401
from tests.presentation.test_plan_api import PERSONA_B


def build_lessons(content_dir: Path, lesson_ids: list[str]) -> None:
    """Make more plan lessons built: copies of the variant-free m1_l2 fixture lesson."""
    rules_path = content_dir / "plan-rules.json"
    rules = json.loads(rules_path.read_text())
    for module in rules["modules"]:
        for lesson in module["lessons"]:
            if lesson["id"] in lesson_ids:
                lesson["built"] = True
    rules_path.write_text(json.dumps(rules))
    source = json.loads((content_dir / "lessons" / "m1_l2.json").read_text())
    for lesson_id in lesson_ids:
        copy_ = copy.deepcopy(source)
        copy_["id"] = lesson_id
        (content_dir / "lessons" / f"{lesson_id}.json").write_text(json.dumps(copy_))


def lessons_by_id(body: dict[str, object]) -> dict[str, dict[str, object]]:
    modules: list[dict[str, list[dict[str, object]]]] = body["modules"]  # type: ignore[assignment]
    return {str(x["id"]): x for m in modules for x in m["lessons"]}


# --- phrases ---


async def test_save_phrase_then_list_then_delete(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    r = await pclient.post(
        "/api/phrases", json={"text": "I'm here.", "source": "scenario", "lessonId": "m1_l1"}
    )
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["text"] == "I'm here." and saved["lessonId"] == "m1_l1"
    assert saved["source"] == "scenario" and saved["savedAt"]
    listed = (await pclient.get("/api/phrases")).json()["phrases"]
    assert [p["id"] for p in listed] == [saved["id"]]
    assert (await pclient.delete(f"/api/phrases/{saved['id']}")).status_code == 204
    assert (await pclient.get("/api/phrases")).json() == {"phrases": []}


async def test_phrase_over_length_422(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    await subscribe(pclient)
    for body in (
        {"text": "x" * 301, "source": "gift"},
        {"text": "", "source": "gift"},
        {"text": "   ", "source": "gift"},
        {"text": "ok", "source": "elsewhere"},
        {"text": "ok", "source": "gift", "lessonId": "l" * 65},
    ):
        r = await pclient.post("/api/phrases", json=body)
        assert r.status_code == 422, body
        assert r.json()["error"]["code"] in {"validation_error", "invalid_phrase"}
    assert (await pclient.get("/api/phrases")).json() == {"phrases": []}


async def test_phrase_cap_per_session_rejected_with_message(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    for i in range(MAX_PHRASES_PER_SESSION):
        r = await pclient.post("/api/phrases", json={"text": f"p{i}", "source": "roleplay"})
        assert r.status_code == 201
    r = await pclient.post("/api/phrases", json={"text": "one more", "source": "roleplay"})
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "phrase_limit_reached" and "Remove one" in error["message"]
    assert error["details"] == {"limit": MAX_PHRASES_PER_SESSION}


async def test_delete_other_sessions_phrase_returns_404(
    pclient: httpx.AsyncClient,  # noqa: F811
) -> None:
    await subscribe(pclient)
    saved = (await pclient.post("/api/phrases", json={"text": "mine", "source": "gift"})).json()
    token = (await pclient.post("/api/session")).json()["token"]
    for question, value in PERSONA_B.items():
        await pclient.put(
            f"/api/quiz/answers/{question}",
            json={"value": value},
            headers={"X-Session-Token": token},
        )
    await pclient.post("/api/quiz/complete", headers={"X-Session-Token": token})
    await pclient.post(
        "/api/billing/demo", json={"autoRenewConsent": True}, headers={"X-Session-Token": token}
    )
    r = await pclient.delete(f"/api/phrases/{saved['id']}", headers={"X-Session-Token": token})
    assert r.status_code == 404 and r.json()["error"]["code"] == "phrase_not_found"
    assert (await pclient.delete(f"/api/phrases/{saved['id']}")).status_code == 204


async def test_phrases_require_subscription_402(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    assert (await pclient.get("/api/phrases")).status_code == 402
    r = await pclient.post("/api/phrases", json={"text": "a", "source": "gift"})
    assert r.status_code == 402


# --- plan ---


async def test_plan_requires_subscription_402(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    r = await pclient.get("/api/plan")
    assert r.status_code == 402 and r.json()["error"]["details"] == {"reason": "no_plan"}


async def test_plan_endpoint_statuses(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    """Fixture content builds m1_l1 and m1_l2 only; the rest is coming later."""
    await subscribe(pclient)
    body = (await pclient.get("/api/plan")).json()
    lessons = lessons_by_id(body)
    start = date.fromisoformat("2026-01-05")
    assert lessons["m1_l1"]["status"] == "available" and lessons["m1_l1"]["unlockOn"] == str(start)
    assert lessons["m1_l2"]["status"] == "locked"
    assert lessons["m1_l2"]["unlockOn"] == str(start + timedelta(days=2))  # ceil(1 * 7 / 4)
    assert lessons["m1_l3"]["status"] == "coming_later" and lessons["m1_l3"]["unlockOn"] is None
    assert body["heroLessonId"] == "m1_l1" and body["lessonsPerWeek"] == 4
    first = body["modules"][0]
    assert first["reason"] and first["title"]

    clock: FixedClock = db_app.state.clock
    await pclient.get("/api/lessons/m1_l1")
    assert lessons_by_id((await pclient.get("/api/plan")).json())["m1_l1"]["status"] == (
        "in_progress"
    )
    await pclient.post("/api/lessons/m1_l1/complete")
    clock.advance(timedelta(days=2))
    lessons = lessons_by_id((await pclient.get("/api/plan")).json())
    assert lessons["m1_l1"]["status"] == "done" and lessons["m1_l2"]["status"] == "available"


async def test_plan_statuses_follow_the_four_a_week_formula_when_all_built(
    db_app: FastAPI,
    db_client: httpx.AsyncClient,
    tmp_path: Path,
) -> None:
    from tests.lesson_content import make_content_dir

    content_dir = make_content_dir(tmp_path / "content")
    build_lessons(content_dir, ["m1_l3", "m1_l4", "m1_l5"])
    db_app.state.content = JsonContentProvider.from_directory(content_dir)
    db_client.headers["X-Session-Token"] = (await db_client.post("/api/session")).json()["token"]
    await subscribe(db_client)
    lessons = lessons_by_id((await db_client.get("/api/plan")).json())
    start = date.fromisoformat("2026-01-05")
    assert lessons["m1_l1"]["status"] == "available"
    expected = {"m1_l2": 2, "m1_l3": 4, "m1_l4": 6, "m1_l5": 7}
    for lesson_id, offset in expected.items():
        assert lessons[lesson_id]["status"] == "locked", lesson_id
        assert lessons[lesson_id]["unlockOn"] == str(start + timedelta(days=offset)), lesson_id


async def test_plan_after_marking_built_appends_schedule(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    tmp_path: Path,
) -> None:
    await subscribe(pclient)
    before = lessons_by_id((await pclient.get("/api/plan")).json())
    assert before["m1_l3"]["status"] == "coming_later"
    build_lessons(tmp_path / "content", ["m1_l3"])
    db_app.state.content = JsonContentProvider.from_directory(tmp_path / "content")
    after = lessons_by_id((await pclient.get("/api/plan")).json())
    assert after["m1_l3"]["status"] == "locked"
    assert str(after["m1_l3"]["unlockOn"]) > str(after["m1_l2"]["unlockOn"])
    assert after["m1_l1"] == before["m1_l1"] and after["m1_l2"] == before["m1_l2"]  # not moved


# --- recap over HTTP ---


async def test_lesson_recap_over_http(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    await subscribe(pclient)
    assert (await pclient.get("/api/lessons/m1_l1")).json()["recap"] is None
    await pclient.post(
        "/api/phrases",
        json={"text": "Let's sit together.", "source": "roleplay", "lessonId": "m1_l1"},
    )
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=10))
    recap = (await pclient.get("/api/lessons/m1_l2")).json()["recap"]
    assert recap["fromLessonId"] == "m1_l1"
    assert 'Your phrase was: "Let\'s sit together."' in recap["text"]
