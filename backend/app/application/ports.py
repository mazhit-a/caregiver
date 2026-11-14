"""Ports (Protocols) that infrastructure adapters implement."""

from collections.abc import Mapping
from datetime import date, datetime
from types import TracebackType
from typing import Any, Protocol, Self
from uuid import UUID

from app.domain.safety.resources import CrisisResource
from app.domain.session.entities import Session
from app.domain.shared.labels import RecipientLabels


class Clock(Protocol):
    """Source of app time (real now plus session offset). Never call datetime.now() elsewhere."""

    def now(self) -> datetime: ...


class SessionRepository(Protocol):
    async def add(self, session: Session) -> None: ...

    async def get_by_token_hash(self, token_hash: str) -> Session | None: ...

    async def save(self, session: Session) -> None:
        """Persist the mutable fields (offset, last_seen_at, recipient_key, display_name)."""
        ...


class ActiveDayRepository(Protocol):
    async def record(self, session_id: UUID, day: date) -> bool:
        """Record an active app day once; True when newly recorded, False if already there."""
        ...

    async def list_days(self, session_id: UUID) -> list[date]: ...


class UnitOfWork(Protocol):
    """Transaction boundary: `async with uow:` ... `await uow.commit()`.

    Repositories are attributes of the unit of work; they never commit themselves.
    """

    sessions: SessionRepository
    active_days: ActiveDayRepository

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


class IdGenerator(Protocol):
    """Generates internal row ids (UUIDs) so that domain and use cases never call uuid4."""

    def new_id(self) -> UUID: ...


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

    def crisis_resources(self) -> list[CrisisResource]: ...

    def crisis_resources_need_verification(self) -> bool:
        """True while the phone numbers are still marked "to be verified before launch"."""
        ...
