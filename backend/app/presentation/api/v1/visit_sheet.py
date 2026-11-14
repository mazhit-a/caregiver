"""Visit sheet routes (behind the access gate). Bodies hold family notes: never logged.
There is deliberately no public or shared route for the sheet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.visit_sheet.use_cases import (
    GetVisitSheet,
    UpdateVisitSheet,
    VisitSheetInput,
    VisitSheetView,
)
from app.domain.visit_sheet.entities import VisitQuestionItem
from app.presentation.api.deps import SubscribedSession, get_clock, get_uow
from app.presentation.api.schemas.visit_sheet import (
    BankQuestionOut,
    QuestionOut,
    SuggestedNoteOut,
    VisitSheetRequest,
    VisitSheetResponse,
)

router = APIRouter(tags=["visit-sheet"])


def _get(request: Request, uow: Annotated[UnitOfWork, Depends(get_uow)]) -> GetVisitSheet:
    content: ContentProvider = request.app.state.content
    return GetVisitSheet(uow, content)


def _update(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> UpdateVisitSheet:
    content: ContentProvider = request.app.state.content
    return UpdateVisitSheet(uow, content, clock)


def _out(view: VisitSheetView) -> VisitSheetResponse:
    return VisitSheetResponse(
        doctor=view.doctor,
        visit_date=view.visit_date,
        family_notes=view.family_notes,
        questions=[QuestionOut(id=q.id, text=q.text, custom=q.custom) for q in view.questions],
        bank=[BankQuestionOut(id=q.id, text=q.text) for q in view.bank],
        suggested_notes=[
            SuggestedNoteOut(id=n.id, text=n.text, created_at=n.created_at)
            for n in view.suggested_notes
        ],
        footer=view.footer,
        updated_at=view.updated_at,
    )


@router.get("/visit-sheet", response_model=VisitSheetResponse)
async def get_visit_sheet(
    session: SubscribedSession, use_case: Annotated[GetVisitSheet, Depends(_get)]
) -> VisitSheetResponse:
    return _out(await use_case.execute(session))


@router.put("/visit-sheet", response_model=VisitSheetResponse)
async def put_visit_sheet(
    body: VisitSheetRequest,
    session: SubscribedSession,
    use_case: Annotated[UpdateVisitSheet, Depends(_update)],
) -> VisitSheetResponse:
    data = VisitSheetInput(
        body.doctor,
        body.visit_date,
        body.family_notes,
        tuple(VisitQuestionItem(q.id, q.text) for q in body.questions),
    )
    return _out(await use_case.execute(session, data))
