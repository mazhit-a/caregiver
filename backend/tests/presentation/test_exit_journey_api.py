"""Increment 37: after a full journey, gentle exit and clear-data leave zero rows for the session
in every table that has a `session_id` column (real Postgres, real app)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.presentation.test_checkins_api import make_plan
from tests.presentation.test_lessons_api import _answer, pclient  # noqa: F401

RATINGS = {"repeat": 3, "accusations": 2, "evenings": 4, "refusal": 1, "visits": 5}

# Session-owned tables the journey fills (`sessions` itself has `id`, not `session_id`).
EXPECTED_TABLES = {
    "active_days",
    "care_cards",
    "checkins",
    "confidence",
    "events",
    "if_then_plans",
    "lesson_progress",
    "lesson_schedule",
    "observations",
    "plans",
    "profiles",
    "quiz_states",
    "roleplay_runs",
    "saved_phrases",
    "scenario_answers",
    "subscription_history",
    "subscriptions",
    "tasks",
    "visit_sheets",
}


async def _session_tables(factory: async_sessionmaker[AsyncSession]) -> set[str]:
    async with factory() as db:
        rows = await db.execute(
            text(
                "SELECT c.table_name FROM information_schema.columns c "
                "JOIN information_schema.tables t USING (table_schema, table_name) "
                "WHERE c.table_schema = 'public' AND c.column_name = 'session_id' "
                "AND t.table_type = 'BASE TABLE'"
            )
        )
        return {r[0] for r in rows}


async def _journey(
    client: httpx.AsyncClient, app: FastAPI, factory: async_sessionmaker[AsyncSession]
) -> UUID:
    await make_plan(client)  # quiz, demo subscription, answers, if-then plan, task
    assert (await _answer(client, "scenario", "a3")).status_code == 200
    assert (await _answer(client, "wrap", RATINGS)).status_code == 200
    assert (await client.post("/api/lessons/m1_l1/complete")).status_code == 200
    app.state.clock.advance(timedelta(days=1))
    r = await client.post(
        "/api/checkins",
        json={
            "planId": "m1_l1",
            "cameUp": "yes",
            "outcome": "helped",
            "doctorNote": {"addToVisitSheet": True, "text": "At dinner"},
        },
    )
    assert r.status_code == 200, r.text
    r = await client.post("/api/phrases", json={"text": "I am here.", "source": "scenario"})
    assert r.status_code in (200, 201), r.text
    assert (await client.put("/api/profile", json={"displayName": "Margaret"})).status_code == 200
    assert (
        await client.put("/api/visit-sheet", json={"familyNotes": "Slept badly"})
    ).status_code == 200
    assert (await client.post("/api/care-card", json={})).status_code in (200, 201)
    r = await client.post("/api/events", json={"events": [{"name": "quiz_start"}]})
    assert r.status_code == 200, r.text
    async with factory() as db:
        sid = (await db.execute(text("SELECT id FROM sessions"))).scalar_one()
        await db.execute(
            text(
                "INSERT INTO roleplay_runs (id, session_id, lesson_id, context, mode, rounds_total,"
                " started_at) VALUES (gen_random_uuid(), :s, 'm1_l1', 'lesson', 'ai', 3, :t)"
            ),
            {"s": sid, "t": datetime(2026, 1, 5, tzinfo=UTC)},
        )
        await db.commit()
    assert isinstance(sid, UUID)
    return sid


async def _row_counts(
    factory: async_sessionmaker[AsyncSession], tables: set[str], sid: UUID
) -> dict[str, int]:
    counts: dict[str, int] = {}
    async with factory() as db:
        for table in sorted(tables):
            sql = f"SELECT count(*) FROM {table} WHERE session_id = :s"  # noqa: S608
            counts[table] = int(await db.scalar(text(sql), {"s": sid}) or 0)
        counts["sessions"] = int(
            await db.scalar(text("SELECT count(*) FROM sessions WHERE id = :s"), {"s": sid}) or 0
        )
    return counts


@pytest.mark.parametrize(
    ("method", "url"), [("post", "/api/exit/gentle"), ("delete", "/api/session")]
)
async def test_gentle_exit_leaves_no_row_for_the_session_in_any_table(
    method: str,
    url: str,
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    tables = await _session_tables(session_factory)
    assert tables == EXPECTED_TABLES  # a new session table must be added to the journey
    sid = await _journey(pclient, db_app, session_factory)
    card_id = (await pclient.get("/api/care-card")).json()["link"].rstrip("/").rsplit("/", 1)[-1]

    before = await _row_counts(session_factory, tables, sid)
    empty = [t for t, count in before.items() if count < 1]
    assert not empty, empty  # the journey filled every table

    r = await getattr(pclient, method)(url)
    assert r.status_code == 200, r.text

    after = await _row_counts(session_factory, tables, sid)
    assert after == dict.fromkeys(after, 0), after
    pclient.headers.pop("X-Session-Token")
    assert (await pclient.get(f"/api/cards/{card_id}")).status_code == 404


async def test_every_session_foreign_key_cascades_on_delete(
    pclient: httpx.AsyncClient,  # noqa: F811
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT conrelid::regclass::text, confdeltype::text FROM pg_constraint "
                    "WHERE contype = 'f' AND confrelid = 'sessions'::regclass"
                )
            )
        ).all()
    tables = {name for name, _ in rows}
    assert tables == await _session_tables(session_factory)
    assert all(kind == "c" for _, kind in rows), rows


@pytest.mark.parametrize(
    ("method", "url"), [("post", "/api/exit/gentle"), ("delete", "/api/session")]
)
async def test_gentle_exit_deletes_events_rows(
    method: str,
    url: str,
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    sid = await _journey(pclient, db_app, session_factory)
    before = await _row_counts(session_factory, {"events"}, sid)
    assert before["events"] >= 3  # client event + lesson_complete + checkin_answer ...
    assert (await getattr(pclient, method)(url)).status_code == 200
    assert (await _row_counts(session_factory, {"events"}, sid))["events"] == 0
