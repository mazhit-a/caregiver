from datetime import UTC, date, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.tokens import SecretsTokenGenerator
from app.presentation.api.deps import CurrentSession
from tests.fakes.clock import FixedClock


def add_probe_route(app: FastAPI) -> None:
    @app.get("/api/_probe")
    async def probe(session: CurrentSession) -> dict[str, str]:
        return {"timezone": session.timezone}


async def create(client: httpx.AsyncClient, body: dict[str, str] | None = None) -> str:
    response = await client.post("/api/session", json=body)
    assert response.status_code == 201
    token: str = response.json()["token"]
    return token


def test_token_generator_gives_at_least_32_bytes_urlsafe() -> None:
    token = SecretsTokenGenerator().new_token()
    assert len(token) >= 43  # 32 bytes, base64url without padding
    assert set(token) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


async def test_token_is_at_least_32_bytes_and_only_hash_is_stored(
    db_client: httpx.AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    response = await db_client.post("/api/session", json={"timezone": "Europe/Berlin"})
    assert response.status_code == 201
    body = response.json()
    assert len(body["token"]) >= 43
    assert body["timezone"] == "Europe/Berlin"
    async with session_factory() as db:
        rows = (await db.execute(text("SELECT * FROM sessions"))).mappings().all()
    assert len(rows) == 1
    assert "token" not in rows[0]
    assert len(rows[0]["token_hash"]) == 64
    assert body["token"] not in [str(v) for v in rows[0].values()]


async def test_default_timezone_when_body_missing_or_empty(db_client: httpx.AsyncClient) -> None:
    for kwargs in ({}, {"json": {}}):
        response = await db_client.post("/api/session", **kwargs)
        assert response.status_code == 201
        assert response.json()["timezone"] == "America/New_York"


async def test_invalid_timezone_returns_422(db_client: httpx.AsyncClient) -> None:
    response = await db_client.post("/api/session", json={"timezone": "Mars/Olympus"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_timezone"
    assert set(error) == {"code", "message", "details"}


async def test_missing_or_wrong_token_returns_401_in_error_shape(
    db_app: FastAPI, db_client: httpx.AsyncClient
) -> None:
    add_probe_route(db_app)
    for headers in ({}, {"X-Session-Token": "wrong"}):
        response = await db_client.get("/api/_probe", headers=headers)
        assert response.status_code == 401
        error = response.json()["error"]
        assert error["code"] == "invalid_session_token"
        assert set(error) == {"code", "message", "details"}


async def test_authenticated_request_records_active_day_once_per_app_day(
    db_app: FastAPI,
    db_client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    add_probe_route(db_app)
    clock: FixedClock = db_app.state.clock
    clock.set(datetime(2026, 1, 5, 15, 0, tzinfo=UTC))  # 10:00 in New York
    token = await create(db_client)
    headers = {"X-Session-Token": token}

    for _ in range(2):
        assert (await db_client.get("/api/_probe", headers=headers)).status_code == 200
    assert await days(session_factory) == [date(2026, 1, 5)]

    clock.advance(timedelta(hours=24))
    assert (await db_client.get("/api/_probe", headers=headers)).status_code == 200
    assert await days(session_factory) == [date(2026, 1, 5), date(2026, 1, 6)]

    async with session_factory() as db:
        last_seen = await db.scalar(text("SELECT last_seen_at FROM sessions"))
    assert last_seen == clock.now()


async def days(factory: async_sessionmaker[AsyncSession]) -> list[date]:
    async with factory() as db:
        result = await db.execute(text("SELECT day FROM active_days ORDER BY day"))
        return list(result.scalars())
