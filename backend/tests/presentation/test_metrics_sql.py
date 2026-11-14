"""`scripts/metrics.sql`: every query executes on the Postgres test DB and gives sensible numbers
on fixture data (the real app fills the tables)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.fakes.clock import FixedClock
from tests.presentation.test_lessons_api import pclient, subscribe  # noqa: F401

METRICS = Path(__file__).resolve().parents[2] / "scripts" / "metrics.sql"
FUNNEL = ["landing_view", "quiz_start", "quiz_complete", "plan_preview_view", "paywall_view"]


def load_queries() -> dict[str, str]:
    queries: dict[str, str] = {}
    name = ""
    for line in METRICS.read_text().splitlines():
        if line.startswith("-- name:"):
            name = line.removeprefix("-- name:").strip()
            queries[name] = ""
        elif name:
            queries[name] += line + "\n"
    return queries


async def run_all(factory: async_sessionmaker[AsyncSession]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    async with factory() as db:
        for name, sql in load_queries().items():
            result = await db.execute(text(sql))
            out[name] = [dict(r._mapping) for r in result]
    return out


async def test_metrics_sql_has_all_five_queries() -> None:
    assert set(load_queries()) == {
        "funnel",
        "d0_lesson_start",
        "first_roleplay_completed",
        "lesson_1_to_2_start",
        "active_days_week_1",
    }


async def test_metrics_queries_run_on_an_empty_database(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    result = await run_all(session_factory)
    assert [r["sessions"] for r in result["funnel"]] == [0] * 6
    assert result["d0_lesson_start"][0]["subscribers"] == 0
    assert result["d0_lesson_start"][0]["pct"] is None  # no division by zero
    assert result["active_days_week_1"] == []


async def test_metrics_queries_return_sensible_numbers_on_fixture_data(
    pclient: httpx.AsyncClient,  # noqa: F811
    db_app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    events = [{"name": n} for n in FUNNEL]
    assert (await pclient.post("/api/events", json={"events": events})).status_code == 200
    await subscribe(pclient)  # demo subscription on app day 0
    assert (await pclient.get("/api/lessons/m1_l1")).status_code == 200  # starts lesson 1
    async with session_factory() as db:
        sid = (await db.execute(text("SELECT id FROM sessions"))).scalar_one()
        await db.execute(
            text(
                "INSERT INTO roleplay_runs (id, session_id, lesson_id, context, mode, rounds_total,"
                " started_at, finished_at) VALUES (gen_random_uuid(), :s, 'm1_l1', 'lesson', 'ai',"
                " 3, :t, :t)"
            ),
            {"s": sid, "t": datetime(2026, 1, 5, tzinfo=UTC)},
        )
        await db.execute(
            text(
                "INSERT INTO lesson_progress (session_id, lesson_id, started_at) "
                "SELECT session_id, lesson_id, :t FROM lesson_schedule WHERE seq = 1"
            ),
            {"t": datetime(2026, 1, 8, tzinfo=UTC)},
        )
        await db.commit()
    clock: FixedClock = db_app.state.clock
    clock.advance(timedelta(days=2))
    await pclient.get("/api/today")  # an authenticated request records the app day

    result = await run_all(session_factory)
    funnel = result["funnel"]
    assert [r["step"] for r in funnel][-1] == "subscribe"
    assert [r["sessions"] for r in funnel] == [1] * 6
    assert float(funnel[-1]["pct_of_landing"]) == 100.0
    d0 = result["d0_lesson_start"][0]
    assert d0["subscribers"] == 1 and d0["started_lesson_1_on_day_0"] == 1
    assert float(d0["pct"]) == 100.0
    assert result["first_roleplay_completed"][0]["finished_a_roleplay"] == 1
    l12 = result["lesson_1_to_2_start"][0]
    assert l12["started_lesson_1"] == 1 and l12["started_lesson_2"] == 1
    days = {r["active_days"]: r["sessions"] for r in result["active_days_week_1"]}
    assert sum(days.values()) == 1 and max(days) >= 2  # day 0 and day 2 (both inside week 1)
