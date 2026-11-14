"""Product events: a batch of whitelisted funnel/app events. Behind the session only (the funnel
starts before any subscription)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.events.use_cases import EventInput, RecordEvents
from app.application.ports import Clock, UnitOfWork
from app.presentation.api.deps import CurrentSession, get_clock, get_uow
from app.presentation.api.schemas.events import EventsRequest, EventsResponse

router = APIRouter(tags=["events"])


def _record(
    uow: Annotated[UnitOfWork, Depends(get_uow)], clock: Annotated[Clock, Depends(get_clock)]
) -> RecordEvents:
    return RecordEvents(uow, clock)


@router.post("/events", response_model=EventsResponse)
async def post_events(
    body: EventsRequest,
    session: CurrentSession,
    use_case: Annotated[RecordEvents, Depends(_record)],
) -> EventsResponse:
    stored = await use_case.execute(session, [EventInput(e.name, e.props) for e in body.events])
    return EventsResponse(stored=stored)
