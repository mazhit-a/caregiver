import json
import logging
import re
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.content.provider import JsonContentProvider

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
async def qclient(
    db_app: FastAPI, db_client: httpx.AsyncClient
) -> AsyncIterator[httpx.AsyncClient]:
    # The ASGI test transport does not run the lifespan, so load the content here.
    db_app.state.content = JsonContentProvider.from_directory(REPO / "content")
    response = await db_client.post("/api/session")
    db_client.headers["X-Session-Token"] = response.json()["token"]
    yield db_client


async def _put(client: httpx.AsyncClient, question: str, value: object) -> httpx.Response:
    return await client.put(f"/api/quiz/answers/{question}", json={"value": value})


async def test_unknown_option_id_rejected_422(qclient: httpx.AsyncClient) -> None:
    r = await _put(qclient, "q2_age", "ancient")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_answer"
    assert "ancient" not in r.text


async def test_unknown_question_404_and_interstitial_not_answerable(
    qclient: httpx.AsyncClient,
) -> None:
    assert (await _put(qclient, "q99", "x")).status_code == 404
    assert (await _put(qclient, "reassure_1", "x")).status_code == 404


async def test_requires_session_token(db_client: httpx.AsyncClient, db_app: FastAPI) -> None:
    db_app.state.content = JsonContentProvider.from_directory(REPO / "content")
    assert (await db_client.get("/api/quiz")).status_code == 401


async def test_answer_then_resume_through_api(qclient: httpx.AsyncClient) -> None:
    r = await _put(qclient, "q1_recipient", "mom")
    assert r.status_code == 200
    assert r.json()["lastQuestionId"] == "q1_recipient"
    await _put(qclient, "q3_situation", "hospital")
    await _put(qclient, "q5_changes", [])
    body = (await qclient.get("/api/quiz")).json()
    assert body["lastQuestionId"] == "q5_changes"
    assert body["branch"] == "changing"
    assert body["answers"]["q1_recipient"] == "mom"
    assert body["answers"]["q3_situation"] == "hospital"
    assert not re.search(r"\{\w+\}", json.dumps(body["questions"]))
    assert any("How old is Mom?" in str(q) for q in body["questions"])


async def test_quiz_locked_returns_409(
    qclient: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    assert (await _put(qclient, "q1_recipient", "mom")).status_code == 200
    async with session_factory() as db:
        await db.execute(text("UPDATE quiz_states SET locked = true"))
        await db.commit()
    r = await _put(qclient, "q2_age", "65_74")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "quiz_locked"


async def test_quiz_routes_do_not_log_request_body(
    qclient: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await _put(qclient, "q5_changes", ["evenings", "accuses"])
    await _put(qclient, "q10_documents", {"healthcare_proxy": "missing"})  # invalid: 422 path
    await _put(qclient, "q11_confidence", 2)
    await qclient.get("/api/quiz?secret=zzz")
    # Only the server side: the httpx test client logs its own request line.
    logged = "\n".join(r.getMessage() for r in caplog.records if not r.name.startswith("httpx"))
    assert "PUT /api/quiz/answers/q5_changes" in logged
    for value in ("evenings", "accuses", "missing", "zzz"):
        assert value not in logged
