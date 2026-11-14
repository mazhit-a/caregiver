from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.lessons.progress import LessonProgress
from app.domain.session.entities import Session
from app.infrastructure.db.repositories.lesson_progress import SqlLessonProgressRepository
from app.infrastructure.db.repositories.sessions import SqlSessionRepository
from tests.fakes.lesson_progress import InMemoryLessonProgressRepository

SID = UUID(int=11)
NOW = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def progress() -> LessonProgress:
    return LessonProgress(
        SID, "m1_l1", NOW, variant="phone", step=2, screen_answers={"s1": "phone"}
    )


async def test_in_memory_roundtrip_and_update() -> None:
    repo = InMemoryLessonProgressRepository()
    assert await repo.get(SID, "m1_l1") is None
    await repo.save(progress())
    stored = await repo.get(SID, "m1_l1")
    assert stored == progress()
    assert stored is not None
    stored.step = 5
    await repo.save(stored)
    updated = await repo.get(SID, "m1_l1")
    assert updated is not None and updated.step == 5


async def test_postgres_roundtrip_upsert_and_cascade_delete(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as db:
        await SqlSessionRepository(db).add(
            Session(SID, "hash-progress", "UTC", timedelta(0), NOW, NOW)
        )
        repo = SqlLessonProgressRepository(db)
        await repo.save(progress())
        assert await repo.get(SID, "m1_l1") == progress()
        changed = progress()
        changed.step = 6
        changed.done_at = NOW
        await repo.save(changed)  # upsert
        assert await repo.get(SID, "m1_l1") == changed
        await db.execute(text("DELETE FROM sessions WHERE id = :i"), {"i": SID})
        assert await repo.get(SID, "m1_l1") is None
        await db.rollback()
