from dataclasses import replace
from datetime import date
from uuid import UUID, uuid5

from app.domain.session.entities import Session

_NAMESPACE = UUID("00000000-0000-0000-0000-000000000001")


class InMemorySessionRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, Session] = {}

    async def add(self, session: Session) -> None:
        if any(s.token_hash == session.token_hash for s in self.rows.values()):
            raise ValueError("duplicate token_hash")
        self.rows[session.id] = replace(session)

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        for stored in self.rows.values():
            if stored.token_hash == token_hash:
                return replace(stored)
        return None

    async def get(self, session_id: UUID) -> Session | None:
        stored = self.rows.get(session_id)
        return replace(stored) if stored else None

    async def save(self, session: Session) -> None:
        self.rows[session.id] = replace(session)

    async def delete(self, session_id: UUID) -> None:
        self.rows.pop(session_id, None)


class InMemoryActiveDayRepository:
    def __init__(self) -> None:
        self.days: dict[UUID, set[date]] = {}

    async def record(self, session_id: UUID, day: date) -> bool:
        days = self.days.setdefault(session_id, set())
        if day in days:
            return False
        days.add(day)
        return True

    async def list_days(self, session_id: UUID) -> list[date]:
        return sorted(self.days.get(session_id, set()))


class FakeTokenGenerator:
    """Returns scripted tokens, or a deterministic 43-character sequence."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        self._tokens = list(tokens or [])
        self._count = 0

    def new_token(self) -> str:
        self._count += 1
        if self._tokens:
            return self._tokens.pop(0)
        return f"fake-token-{self._count:030d}"


class FakeIdGenerator:
    def __init__(self) -> None:
        self._count = 0

    def new_id(self) -> UUID:
        self._count += 1
        return uuid5(_NAMESPACE, str(self._count))
