import httpx
from fastapi import FastAPI

from tests.fakes.roleplay import FakeCoach
from tests.presentation.test_lessons_api import _answer, pclient, subscribe  # noqa: F401
from tests.presentation.test_roleplay_api import REPLY, start, turn

ALLOWED_TOP = {"skills", "confidence", "counts", "next"}
ALLOWED_SKILL = {"id", "label", "roleplay", "scenarios"}
ALLOWED_ROLEPLAY = {"runs", "firstScore", "latestScore", "maxScore"}
ALLOWED_NEXT = {"lessonId", "title", "moduleId", "reason", "status", "unlockOn"}


async def test_skills_requires_subscription_402(pclient: httpx.AsyncClient) -> None:  # noqa: F811
    r = await pclient.get("/api/skills")
    assert r.status_code == 402 and r.json()["error"]["details"] == {"reason": "no_plan"}


async def test_skills_has_no_roleplay_text_fields(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
) -> None:
    db_app.state.coach = FakeCoach()
    await subscribe(pclient)
    body = (await pclient.get("/api/skills")).json()
    assert set(body) == ALLOWED_TOP
    assert set(body["confidence"]) == {"day0", "first", "latest"}
    assert set(body["counts"]) == {
        "scenariosPractised",
        "phrasesSaved",
        "tasksTried",
        "tasksHelped",
    }
    assert set(body["next"]) == ALLOWED_NEXT and body["next"]["lessonId"] == "m1_l1"
    assert body["next"]["reason"] and body["skills"] == []
    run = await start(pclient)
    for answer in ("a1", "a4"):
        r = await _answer(pclient, "scenario", answer)
        assert r.status_code == 200, r.text
    assert (await turn(pclient, run["runId"])).status_code == 200
    phrases = {"phrases": [{"reply": REPLY, "betterPhrase": "Better."}]}
    r = await pclient.post(f"/api/roleplay/{run['runId']}/finish", json=phrases)
    assert r.status_code == 200, r.text
    r = await pclient.get("/api/skills")
    assert REPLY not in r.text and "Better." not in r.text
    skills = r.json()["skills"]
    assert [s["id"] for s in skills] == ["communication"]
    assert set(skills[0]) == ALLOWED_SKILL and set(skills[0]["roleplay"]) == ALLOWED_ROLEPLAY
    assert skills[0]["roleplay"]["firstScore"] == 3
    assert skills[0]["scenarios"] == {"practised": 1, "best": 1}
    assert r.json()["counts"]["scenariosPractised"] == 1
