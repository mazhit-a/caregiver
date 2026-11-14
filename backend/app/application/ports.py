"""Ports (Protocols) that infrastructure adapters implement."""

from datetime import datetime
from types import TracebackType
from typing import Protocol, Self


class Clock(Protocol):
    """Source of app time (real now plus session offset). Never call datetime.now() elsewhere."""

    def now(self) -> datetime: ...


class UnitOfWork(Protocol):
    """Transaction boundary: `async with uow:` ... `await uow.commit()`."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TokenGenerator(Protocol):
    """Generates public, unguessable tokens (session tokens, card ids)."""

    def new_token(self) -> str: ...
