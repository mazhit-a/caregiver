import json
import re
from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.content.provider import JsonContentProvider

REPO = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

PERSONA_B: dict[str, Any] = {
    "q1_recipient": "mom",
    "q2_age": "75_84",
    "q3_situation": "recent",
    "q5_changes": ["repeats", "evenings"],
    "q6_living": "far",
    "q7_helpers": "just_me",
    "q8_work": "full_time",
    "q9_worries": ["what_to_say", "legal_money"],
    "q10_documents": {
        "healthcare_proxy": "missing",
        "financial_poa": "not_sure",
        "hipaa_release": "have",
    },
    "q11_confidence": 2,
    "q12_time": "10",
}


@pytest.fixture
async def content(db_app: FastAPI) -> JsonContentProvider:
    provider = JsonContentProvider.from_directory(REPO / "content")
    db_app.state.content = provider  # the ASGI test transport does not run the lifespan
    return provider


@pytest.fixture
async def pclient(
    content: JsonContentProvider, db_client: httpx.AsyncClient
) -> AsyncIterator[httpx.AsyncClient]:
    response = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = response.json()["token"]
    yield db_client


async def _answer(client: httpx.AsyncClient, answers: dict[str, Any]) -> None:
    for question, value in answers.items():
        r = await client.put(f"/api/quiz/answers/{question}", json={"value": value})
        assert r.status_code == 200, r.text


async def _complete_b(client: httpx.AsyncClient) -> httpx.Response:
    await _answer(client, PERSONA_B)
    return await client.post("/api/quiz/complete")


async def test_persona_b_journey_complete_then_preview(pclient: httpx.AsyncClient) -> None:
    assert (await _complete_b(pclient)).status_code == 200
    r = await pclient.get("/api/plan/preview")
    assert r.status_code == 200
    body = r.json()
    expected = json.loads((FIXTURES / "persona_b.json").read_text())["expected"]
    assert [m["id"] for m in body["modules"]] == [m["id"] for m in expected["modules"]]
    assert all(m["reason"] for m in body["modules"])
    assert [m["reason"] for m in body["modules"]] == [m["reason"] for m in expected["modules"]]
    assert body["first30Days"] == expected["first30Days"]
    assert [g["id"] for g in body["quickGuides"]] == [g["id"] for g in expected["quickGuides"]]
    assert body["loaderLines"] == expected["loaderLines"]
    assert body["pace"] == expected["pace"]
    assert body["whatWeHeard"] == expected["whatWeHeard"]
    assert body["planIntro"] == expected["planIntro"]


async def test_complete_with_missing_required_answer_returns_422_listing_question_ids(
    pclient: httpx.AsyncClient,
) -> None:
    await _answer(pclient, {"q1_recipient": "mom", "q3_situation": "recent"})
    r = await pclient.post("/api/quiz/complete")
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "quiz_incomplete"
    ids = error["details"]["questionIds"]
    assert "q2_age" in ids and "q11_confidence" in ids and "q12_time" in ids
    assert "q1_recipient" not in ids and "q5_changes" not in ids  # answered / skippable
    assert (await pclient.get("/api/plan/preview")).status_code == 402


async def test_preview_before_complete_returns_402_no_plan(pclient: httpx.AsyncClient) -> None:
    for path in ("/api/plan/preview", "/api/plan/gift"):
        r = await pclient.get(path)
        assert r.status_code == 402
        assert r.json()["error"]["details"]["reason"] == "no_plan"


async def test_plan_requires_session_token(
    content: JsonContentProvider, db_client: httpx.AsyncClient
) -> None:
    assert (await db_client.get("/api/plan/preview")).status_code == 401
    assert (await db_client.post("/api/quiz/complete")).status_code == 401


async def test_plan_snapshot_stores_rules_version_and_content_version(
    pclient: httpx.AsyncClient,
    content: JsonContentProvider,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert (await _complete_b(pclient)).status_code == 200
    async with session_factory() as db:
        row = (
            await db.execute(
                text(
                    "SELECT rules_version, content_version, lessons_per_week, gift_phrase_ids,"
                    " built_at FROM plans"
                )
            )
        ).one()
    assert row.rules_version == content.plan_rules().version
    assert row.content_version == content.content_version
    assert row.lessons_per_week == 4
    assert row.gift_phrase_ids == ["p01", "p02", "p06", "p07", "p03"]
    assert row.built_at is not None
    body = (await pclient.get("/api/plan/preview")).json()
    assert body["rulesVersion"] == row.rules_version
    assert body["contentVersion"] == content.content_version


async def test_content_edit_does_not_reshuffle_stored_plan(
    pclient: httpx.AsyncClient,
    content: JsonContentProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _complete_b(pclient)
    before = (await pclient.get("/api/plan/preview")).json()
    rules = content.plan_rules()
    edited = replace(
        rules,
        version=rules.version + 1,
        modules=tuple(reversed(rules.modules)),
        first_module_reason_by_branch={k: "Changed." for k in rules.first_module_reason_by_branch},
    )
    monkeypatch.setattr(content, "plan_rules", lambda: edited)
    assert (await pclient.get("/api/plan/preview")).json() == before


async def test_complete_stores_confidence_day0(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _complete_b(pclient)
    async with session_factory() as db:
        rows = (await db.execute(text("SELECT day0 FROM confidence"))).all()
    assert [r.day0 for r in rows] == [2]


async def test_edit_answer_then_complete_rebuilds_plan(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _complete_b(pclient)
    first = (await pclient.get("/api/plan/preview")).json()
    await _answer(pclient, {"q3_situation": "noticing", "q11_confidence": 5, "q12_time": "5"})
    assert (await pclient.get("/api/plan/preview")).json() == first  # not rebuilt until complete
    assert (await pclient.post("/api/quiz/complete")).status_code == 200
    second = (await pclient.get("/api/plan/preview")).json()
    assert [m["id"] for m in second["modules"]][:2] == ["m1_talking", "m0_before"]
    assert second["pace"]["lessonsPerWeek"] == 3
    assert second["modules"] != first["modules"]
    async with session_factory() as db:
        assert [r.day0 for r in (await db.execute(text("SELECT day0 FROM confidence"))).all()] == [
            5
        ]
        assert (await db.execute(text("SELECT count(*) FROM plans"))).scalar_one() == 1


async def test_gift_has_five_phrases_and_footer(
    pclient: httpx.AsyncClient, content: JsonContentProvider
) -> None:
    await _complete_b(pclient)
    r = await pclient.get("/api/plan/gift")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Phrases that calm Mom"
    assert len(body["phrases"]) == 5
    assert all(p["text"] and p["when"] for p in body["phrases"])
    assert [p["id"] for p in body["phrases"]][:2] == ["p01", "p02"]
    assert body["footer"] == content.phrase_sheet().footer


async def test_gift_and_preview_have_no_placeholder_or_price_per_day(
    pclient: httpx.AsyncClient,
) -> None:
    await _complete_b(pclient)
    for path in ("/api/plan/preview", "/api/plan/gift"):
        raw = (await pclient.get(path)).text
        assert not re.search(r"\{\w+\}", raw)
        assert not re.search(r"per day|a day|/ ?day", raw, re.IGNORECASE)


async def test_locked_quiz_cannot_be_completed_again_and_plan_is_kept(
    pclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await _complete_b(pclient)
    before = (await pclient.get("/api/plan/preview")).json()
    async with session_factory() as db:
        await db.execute(text("UPDATE quiz_states SET locked = true"))
        await db.commit()
    r = await pclient.post("/api/quiz/complete")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "quiz_locked"
    assert (await pclient.get("/api/plan/preview")).json() == before
