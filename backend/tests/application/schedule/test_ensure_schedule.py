from datetime import date
from uuid import UUID

from app.application.schedule.use_cases import EnsureSchedule
from app.domain.schedule.entities import PlanLessonRef, UnlockRule
from tests.fakes.unit_of_work import FakeUnitOfWork

SID = UUID(int=1)
RULE = UnlockRule(7, 0)
START = date(2026, 1, 5)


def lessons(built: list[bool]) -> list[PlanLessonRef]:
    return [PlanLessonRef(f"l{i + 1}", b) for i, b in enumerate(built)]


async def test_creates_schedule_for_built_lessons_only() -> None:
    uow = FakeUnitOfWork()
    rows = await EnsureSchedule(uow).execute(SID, START, 4, lessons([True, True, False]), RULE)
    assert [r.lesson_id for r in rows] == ["l1", "l2"]
    assert uow.committed


async def test_extends_on_read_without_changing_existing_dates() -> None:
    uow = FakeUnitOfWork()
    ensure = EnsureSchedule(uow)
    first = await ensure.execute(SID, START, 4, lessons([True, True, False]), RULE)
    second = await ensure.execute(SID, START, 4, lessons([True, True, True]), RULE)
    assert second[:2] == first
    assert [(r.lesson_id, (r.unlock_on - START).days) for r in second[2:]] == [("l3", 4)]


async def test_second_call_with_nothing_new_writes_nothing() -> None:
    uow = FakeUnitOfWork()
    ensure = EnsureSchedule(uow)
    await ensure.execute(SID, START, 4, lessons([True]), RULE)
    uow.committed = False
    await ensure.execute(SID, START, 4, lessons([True]), RULE)
    assert not uow.committed
