"""Ports (Protocols) that infrastructure adapters implement."""

from collections.abc import Mapping
from datetime import datetime
from types import TracebackType
from typing import Any, Protocol, Self

from app.domain.shared.labels import RecipientLabels


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


class ContentProvider(Protocol):
    """Read access to validated content. Text is returned with placeholders already filled."""

    @property
    def content_version(self) -> str: ...

    def recipient_keys(self) -> list[str]: ...

    def recipient_labels(self, key: str) -> RecipientLabels:
        """Quiz labels for a Q1 key (`both` is plural: "your parents")."""
        ...

    def lesson_recipient_labels(self, key: str) -> RecipientLabels:
        """Labels for lesson text (`both` becomes the singular "your parent")."""
        ...

    def lesson_ids(self) -> list[str]: ...

    def lesson_variants(self, lesson_id: str) -> list[str]: ...

    def render_lesson(
        self,
        lesson_id: str,
        recipient_key: str,
        variant: str | None = None,
        runtime_values: Mapping[str, str] | None = None,
    ) -> dict[str, Any]: ...
