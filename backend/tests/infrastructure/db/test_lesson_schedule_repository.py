from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.schedule.entities import ScheduledLesson
from app.domain.session.entities import Session
from app.infrastructure.db.repositories.lesson_schedule import SqlLessonScheduleRepository
from app.infrastructure.db.repositories.sessions import SqlSessionRepository
from tests.fakes.lesson_schedule import InMemoryLessonScheduleRepository

SID = UUID(int=7)
ROWS = [ScheduledLesson("l2", 1, date(2026, 1, 7)), ScheduledLesson("l1", 0, date(2026, 1, 5))]


async def test_in_memory_roundtrip_ordered_by_seq() -> None:
    repo = InMemoryLessonScheduleRepository()
    await repo.add_many(SID, ROWS)
    assert [r.lesson_id for r in await repo.list_for_session(SID)] == ["l1", "l2"]
    assert await repo.list_for_session(UUID(int=8)) == []


async def test_postgres_roundtrip_and_cascade_delete(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    async with session_factory() as db:
        await SqlSessionRepository(db).add(
            Session(SID, "hash-sched", "America/New_York", timedelta(0), now, now)
        )
        repo = SqlLessonScheduleRepository(db)
        await repo.add_many(SID, ROWS)
        assert await repo.list_for_session(SID) == sorted(ROWS, key=lambda r: r.seq)
        await db.execute(text("DELETE FROM sessions WHERE id = :i"), {"i": SID})
        assert await repo.list_for_session(SID) == []
        await db.rollback()


async def test_postgres_duplicate_lesson_rejected(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from sqlalchemy.exc import IntegrityError

    now = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    async with session_factory() as db:
        await SqlSessionRepository(db).add(
            Session(SID, "hash-sched2", "America/New_York", timedelta(0), now, now)
        )
        repo = SqlLessonScheduleRepository(db)
        await repo.add_many(SID, ROWS[:1])
        with pytest.raises(IntegrityError):
            await repo.add_many(SID, ROWS[:1])
        await db.rollback()
