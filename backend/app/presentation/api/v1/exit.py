"""Gentle exit and "Clear my data". Behind the session only, never the access gate: both must
work for every subscription status, including `past_due`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.billing.exit import ClearMyData, EraseSession, GentleExit
from app.application.ports import Clock, ContentProvider, PaymentGateway, UnitOfWork
from app.presentation.api.deps import (
    CurrentSession,
    get_clock,
    get_optional_payment_gateway,
    get_uow,
)
from app.presentation.api.schemas.exit import (
    ClearDataResponse,
    GentleExitResponse,
    GrieveResourceOut,
)

router = APIRouter(tags=["exit"])


def _erase(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
    gateway: Annotated[PaymentGateway | None, Depends(get_optional_payment_gateway)],
) -> EraseSession:
    return EraseSession(uow, clock, gateway)


def _gentle_exit(request: Request, erase: Annotated[EraseSession, Depends(_erase)]) -> GentleExit:
    content: ContentProvider = request.app.state.content
    return GentleExit(erase, content)


def _clear_my_data(
    request: Request, erase: Annotated[EraseSession, Depends(_erase)]
) -> ClearMyData:
    content: ContentProvider = request.app.state.content
    return ClearMyData(erase, content)


@router.post("/exit/gentle", response_model=GentleExitResponse)
async def gentle_exit(
    session: CurrentSession, use_case: Annotated[GentleExit, Depends(_gentle_exit)]
) -> GentleExitResponse:
    copy = await use_case.execute(session)
    return GentleExitResponse(
        title=copy.title,
        condolence=copy.condolence,
        resources_intro=copy.resources_intro,
        resources=[
            GrieveResourceOut(
                id=r.id, name=r.name, description=r.description, phone=r.phone, url=r.url
            )
            for r in copy.resources
        ],
    )


@router.delete("/session", response_model=ClearDataResponse)
async def clear_my_data(
    session: CurrentSession, use_case: Annotated[ClearMyData, Depends(_clear_my_data)]
) -> ClearDataResponse:
    return ClearDataResponse(message=await use_case.execute(session))
