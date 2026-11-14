"""DTOs of the session use cases."""

from dataclasses import dataclass

from app.domain.session.entities import Session


@dataclass(frozen=True)
class CreatedSession:
    token: str
    session: Session
