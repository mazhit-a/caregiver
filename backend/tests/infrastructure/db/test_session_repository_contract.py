"""One contract, run against the in-memory fakes and Postgres."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports import ActiveDayRepository, SessionRepository
from app.domain.session.entities import Session
from app.infrastructure.db.repositories.sessions import SqlActiveDayRepository, SqlSessionRepository
from tests.fakes.sessions import InMemoryActiveDayRepository, InMemorySessionRepository


@dataclass
class Repos:
    sessions: SessionRepository
    active_days: ActiveDayRepository


@pytest.fixture
def fake_repos() -> Repos:
    return Repos(InMemorySessionRepository(), InMemoryActiveDayRepository())


@pytest.fixture
async def postgres_repos(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[Repos]:
    async with session_factory() as db:
        yield Repos(SqlSessionRepository(db), SqlActiveDayRepository(db))
        await db.rollback()


@pytest.fixture(params=["fake_repos", "postgres_repos"])
def repos(request: pytest.FixtureRequest) -> Repos:
    repos: Repos = request.getfixturevalue(request.param)
    return repos


def make(n: int, token_hash: str | None = None) -> Session:
    now = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    return Session(
        id=UUID(int=n),
        token_hash=token_hash or f"hash-{n}",
        timezone="America/New_York",
        clock_offset=timedelta(0),
        created_at=now,
        last_seen_at=now,
    )


async def test_add_then_get_by_token_hash_roundtrips(repos: Repos) -> None:
    session = make(1)
    await repos.sessions.add(session)
    assert await repos.sessions.get_by_token_hash("hash-1") == session


async def test_get_unknown_hash_returns_none(repos: Repos) -> None:
    assert await repos.sessions.get_by_token_hash("missing") is None


async def test_save_persists_mutable_fields(repos: Repos) -> None:
    session = make(1)
    await repos.sessions.add(session)
    session.clock_offset = timedelta(hours=24)
    session.last_seen_at += timedelta(days=1)
    session.recipient_key = "mom"
    session.display_name = "Ann"
    await repos.sessions.save(session)
    assert await repos.sessions.get_by_token_hash("hash-1") == session


async def test_duplicate_token_hash_is_rejected(repos: Repos) -> None:
    await repos.sessions.add(make(1, "same"))
    with pytest.raises((ValueError, IntegrityError)):
        await repos.sessions.add(make(2, "same"))


async def test_active_day_is_recorded_once_per_day(repos: Repos) -> None:
    await repos.sessions.add(make(1))
    sid = UUID(int=1)
    assert await repos.active_days.record(sid, date(2026, 1, 5)) is True
    assert await repos.active_days.record(sid, date(2026, 1, 5)) is False
    assert await repos.active_days.record(sid, date(2026, 1, 6)) is True
    assert await repos.active_days.list_days(sid) == [date(2026, 1, 5), date(2026, 1, 6)]


async def test_deleting_a_session_cascades_to_active_days(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as db:
        await SqlSessionRepository(db).add(make(1))
        await SqlActiveDayRepository(db).record(UUID(int=1), date(2026, 1, 5))
        await db.commit()
        await db.execute(text("DELETE FROM sessions"))
        await db.commit()
        assert await SqlActiveDayRepository(db).list_days(UUID(int=1)) == []
