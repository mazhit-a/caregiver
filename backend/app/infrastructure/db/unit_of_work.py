"""SQLAlchemy unit of work: one AsyncSession per `async with`, repositories as attributes."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories.sessions import SqlActiveDayRepository, SqlSessionRepository


class SqlAlchemyUnitOfWork:
    sessions: SqlSessionRepository
    active_days: SqlActiveDayRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory
        self._db: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._db = self._factory()
        self.sessions = SqlSessionRepository(self._db)
        self.active_days = SqlActiveDayRepository(self._db)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        db = self._require()
        try:
            if exc_type is not None:
                await db.rollback()
        finally:
            await db.close()
            self._db = None

    async def commit(self) -> None:
        await self._require().commit()

    async def rollback(self) -> None:
        await self._require().rollback()

    def _require(self) -> AsyncSession:
        if self._db is None:
            raise RuntimeError("UnitOfWork used outside `async with`")
        return self._db
