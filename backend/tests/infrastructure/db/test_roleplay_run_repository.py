from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.roleplay.run import RoleplayRun, RunContext, RunMode, RunRecord
from app.domain.roleplay.verdict import Goals
from app.domain.session.entities import Session
from app.infrastructure.db.repositories.roleplay_runs import SqlRoleplayRunRepository
from app.infrastructure.db.repositories.sessions import SqlSessionRepository
from tests.fakes.roleplay import InMemoryRoleplayRunRepository

SID = UUID(int=21)
RID = UUID(int=22)
NOW = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


def record() -> RunRecord:
    run = RoleplayRun(rounds_total=3)
    run.record_turn(2, Goals(True, True, False))
    return RunRecord(RID, SID, "m1_l1", RunContext.PRACTICE_ROUND, "phone", NOW, run)


async def test_in_memory_roundtrip() -> None:
    repo = InMemoryRoleplayRunRepository()
    assert await repo.get(RID) is None
    await repo.save(record())
    assert await repo.get(RID) == record()


async def test_postgres_roundtrip_update_cascade_and_no_text_columns(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as db:
        await SqlSessionRepository(db).add(
            Session(SID, "hash-roleplay", "UTC", timedelta(0), NOW, NOW)
        )
        repo = SqlRoleplayRunRepository(db)
        await repo.save(record())
        assert await repo.get(RID) == record()
        changed = record()
        changed.run.switch_to_fallback()
        changed.finished_at = NOW + timedelta(minutes=2)
        await repo.save(changed)  # upsert
        stored = await repo.get(RID)
        assert stored == changed and stored.run.mode is RunMode.FALLBACK
        columns = await db.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'roleplay_runs'"
            )
        )
        text_columns = [c for c, t in columns if t in ("text", "character varying")]
        assert sorted(text_columns) == ["context", "lesson_id", "mode", "variant"]
        await db.execute(text("DELETE FROM sessions WHERE id = :i"), {"i": SID})
        assert await repo.get(RID) is None
        await db.rollback()
