"""Check-in route (behind the access gate). The body holds family notes: never logged."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.checkins.use_cases import DoctorNoteInput, SubmitCheckin
from app.application.ports import Clock, ContentProvider, IdGenerator, UnitOfWork
from app.presentation.api.deps import SubscribedSession, get_clock, get_id_generator, get_uow
from app.presentation.api.schemas.checkins import (
    CheckinRequest,
    CheckinResponse,
    FollowUpOut,
    PlanQuoteOut,
)

router = APIRouter(tags=["checkins"])


def _submit(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SubmitCheckin:
    content: ContentProvider = request.app.state.content
    return SubmitCheckin(uow, content, ids, clock)


@router.post("/checkins", response_model=CheckinResponse)
async def submit_checkin(
    body: CheckinRequest,
    session: SubscribedSession,
    use_case: Annotated[SubmitCheckin, Depends(_submit)],
) -> CheckinResponse:
    note = (
        None
        if body.doctor_note is None
        else DoctorNoteInput(body.doctor_note.add_to_visit_sheet, body.doctor_note.text)
    )
    result = await use_case.execute(session, body.plan_id, body.came_up, body.outcome, note)
    return CheckinResponse(
        plan_id=result.plan_id,
        came_up=result.came_up,
        outcome=result.outcome,
        response_text=result.response_text,
        follow_ups=[FollowUpOut(title=f.title, text=f.text) for f in result.follow_ups],
        plan=PlanQuoteOut(
            cue=result.plan.cue, response=result.plan.response, reset=result.plan.reset
        ),
        observation_added=result.observation_added,
        task_done=result.task_done,
    )
