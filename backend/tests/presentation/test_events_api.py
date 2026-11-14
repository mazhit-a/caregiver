"""`POST /api/events` against the real app and Postgres."""

from datetime import timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.fakes.clock import FixedClock
from tests.presentation.test_lessons_api import pclient  # noqa: F401


async def _rows(factory: async_sessionmaker[AsyncSession]) -> list[tuple[str, dict[str, object]]]:
    async with factory() as db:
        result = await db.execute(text("SELECT name, props FROM events ORDER BY id"))
        return [(r[0], r[1]) for r in result]


async def test_events_are_stored_in_app_time_without_the_gate(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=2))
    r = await pclient.post(
        "/api/events",
        json={
            "events": [
                {"name": "landing_view", "props": {"source": "newsletter"}},
                {"name": "quiz_start"},
            ]
        },
    )
    assert r.status_code == 200 and r.json() == {"stored": 2}
    assert await _rows(session_factory) == [
        ("landing_view", {"source": "newsletter"}),
        ("quiz_start", {}),
    ]
    async with session_factory() as db:
        at = (await db.execute(text("SELECT app_at FROM events LIMIT 1"))).scalar_one()
    assert at == clock.now()


async def test_events_reject_unknown_name_422(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    r = await pclient.post(
        "/api/events", json={"events": [{"name": "quiz_start"}, {"name": "drop_table"}]}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unknown_event"
    assert await _rows(session_factory) == []  # the whole batch is rejected


async def test_events_drop_props_not_in_whitelist(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    r = await pclient.post(
        "/api/events",
        json={
            "events": [
                {"name": "paywall_view", "props": {"defaultPlanId": "four_week", "email": "a@b.c"}}
            ]
        },
    )
    assert r.status_code == 200
    assert await _rows(session_factory) == [("paywall_view", {"defaultPlanId": "four_week"})]


async def test_events_never_store_free_text_or_q3_q5_values(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    secret = "mother has dementia and takes donepezil"
    r = await pclient.post(
        "/api/events",
        json={
            "events": [
                {
                    "name": "quiz_answer",
                    "props": {"questionId": "q3", "value": "diagnosed", "answer": secret},
                },
                {"name": "quiz_answer", "props": {"questionId": secret}},
                {"name": "quiz_complete", "props": {"branch": "noticing", "text": secret}},
                {"name": "landing_view", "props": {"source": secret}},
            ]
        },
    )
    assert r.status_code == 200
    rows = await _rows(session_factory)
    assert rows == [
        ("quiz_answer", {"questionId": "q3"}),
        ("quiz_answer", {}),
        ("quiz_complete", {"branch": "noticing"}),
        ("landing_view", {}),
    ]
    assert "diagnosed" not in repr(rows) and "donepezil" not in repr(rows)


async def test_events_batch_over_limit_422(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ok = await pclient.post("/api/events", json={"events": [{"name": "quiz_start"}] * 50})
    assert ok.status_code == 200
    r = await pclient.post("/api/events", json={"events": [{"name": "quiz_start"}] * 51})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    empty = await pclient.post("/api/events", json={"events": []})
    assert empty.status_code == 422
    long = await pclient.post(
        "/api/events", json={"events": [{"name": "landing_view", "props": {"source": "x" * 101}}]}
    )
    assert long.status_code == 422
    assert len(await _rows(session_factory)) == 50


async def test_events_require_a_session(db_client: httpx.AsyncClient) -> None:
    r = await db_client.post("/api/events", json={"events": [{"name": "quiz_start"}]})
    assert r.status_code == 401
