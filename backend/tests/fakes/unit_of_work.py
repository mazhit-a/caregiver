from types import TracebackType
from typing import Self

from tests.fakes.lesson_schedule import InMemoryLessonScheduleRepository
from tests.fakes.quiz import InMemoryQuizStateRepository
from tests.fakes.sessions import InMemoryActiveDayRepository, InMemorySessionRepository


class FakeUnitOfWork:
    """In-memory UnitOfWork scaffold: records commit/rollback; rolls back on error."""

    def __init__(self) -> None:
        self.sessions = InMemorySessionRepository()
        self.active_days = InMemoryActiveDayRepository()
        self.quiz = InMemoryQuizStateRepository()
        self.lesson_schedule = InMemoryLessonScheduleRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
