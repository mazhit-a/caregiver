"""Demo controls: move the session's app clock. 404 unless DEMO_CONTROLS=true."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.demo.dto import DemoState
from app.application.demo.use_cases import AdvanceDemoDay, GetDemoState, JumpToRenewal
from app.application.ports import Clock, UnitOfWork
from app.presentation.api.deps import CurrentSession, get_clock, get_uow, require_demo_controls
from app.presentation.api.schemas.demo import DemoResponse

router = APIRouter(prefix="/demo", tags=["demo"], dependencies=[Depends(require_demo_controls)])

Uow = Annotated[UnitOfWork, Depends(get_uow)]
AppClockDep = Annotated[Clock, Depends(get_clock)]


def _to_response(state: DemoState) -> DemoResponse:
    return DemoResponse(
        app_now=state.app_now,
        app_today=state.app_today,
        clock_offset_seconds=int(state.clock_offset.total_seconds()),
        subscription_status=state.subscription_status,
        current_period_end=state.current_period_end,
        renewal_count=state.renewal_count,
    )


@router.get("", response_model=DemoResponse)
async def get_demo(session: CurrentSession, uow: Uow, clock: AppClockDep) -> DemoResponse:
    return _to_response(await GetDemoState(uow, clock).execute(session))


@router.post("/next-day", response_model=DemoResponse)
async def next_day(session: CurrentSession, uow: Uow, clock: AppClockDep) -> DemoResponse:
    return _to_response(await AdvanceDemoDay(uow, clock).execute(session))


@router.post("/jump-to-renewal", response_model=DemoResponse)
async def jump_to_renewal(session: CurrentSession, uow: Uow, clock: AppClockDep) -> DemoResponse:
    return _to_response(await JumpToRenewal(uow, clock).execute(session))
