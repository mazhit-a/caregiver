from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.events.catalog import clean_event


@dataclass(frozen=True)
class RecordedEvent:
    session_id: UUID
    name: str
    props: dict[str, str | int | bool]
    app_at: datetime


class InMemoryEventLog:
    """Honours the EventLog contract: cleans through the catalog, raises UnknownEvent."""

    def __init__(self) -> None:
        self.events: list[RecordedEvent] = []

    async def record(
        self, session_id: UUID, name: str, props: Mapping[str, object], app_at: datetime
    ) -> None:
        event = clean_event(name, props)
        self.events.append(RecordedEvent(session_id, event.name, event.props, app_at))

    def names(self) -> list[str]:
        return [e.name for e in self.events]
