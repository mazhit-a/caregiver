"""`POST /api/events`: store a batch of whitelisted client events in app time."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.application.ports import Clock, UnitOfWork
from app.domain.events.catalog import MAX_BATCH_SIZE, CleanEvent, clean_event
from app.domain.session.entities import Session


@dataclass(frozen=True)
class EventInput:
    name: str
    props: Mapping[str, object]


class RecordEvents:
    """All names are checked before anything is written, so one unknown name rejects the batch
    (`UnknownEvent`, 422). Props are cleaned by the catalog; the count of stored events is
    returned."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session, events: Sequence[EventInput]) -> int:
        if len(events) > MAX_BATCH_SIZE:
            raise ValueError("The route schema limits the batch size.")
        cleaned: list[CleanEvent] = [clean_event(e.name, e.props) for e in events]
        at = session.app_now(self._clock.now())
        async with self._uow:
            for event in cleaned:
                await self._uow.events.record(session.id, event.name, event.props, at)
            await self._uow.commit()
        return len(cleaned)
