"""Role-play routes (behind the access gate). Request bodies hold the caregiver's reply, so
nothing here logs them (the access log middleware writes method, path and status only)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.application.ports import Clock, ContentProvider, IdGenerator, UnitOfWork
from app.application.roleplay.dto import PreviousTurn, TurnPhrase
from app.application.roleplay.finish import FinishRoleplay
from app.application.roleplay.start import StartRoleplay
from app.application.roleplay.turn import SubmitRoleplayTurn
from app.presentation.api.deps import SubscribedSession, get_clock, get_id_generator, get_uow
from app.presentation.api.roleplay_deps import get_coach_turn_use_case, get_content
from app.presentation.api.schemas.roleplay import (
    FinishRequest,
    FinishResponse,
    StartRequest,
    StartResponse,
    TurnRequest,
    TurnResponse,
    finish_response,
    start_response,
    turn_response,
)

router = APIRouter(prefix="/roleplay", tags=["roleplay"])


def _start(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    content: Annotated[ContentProvider, Depends(get_content)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
) -> StartRoleplay:
    return StartRoleplay(uow, content, clock, ids)


def _finish(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    content: Annotated[ContentProvider, Depends(get_content)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> FinishRoleplay:
    return FinishRoleplay(uow, content, clock)


@router.post("/start", response_model=StartResponse)
async def start(
    body: StartRequest,
    session: SubscribedSession,
    use_case: Annotated[StartRoleplay, Depends(_start)],
) -> StartResponse:
    return start_response(await use_case.execute(session, body.lesson_id, body.context))


@router.post("/{run_id}/turn", response_model=TurnResponse)
async def turn(
    run_id: UUID,
    body: TurnRequest,
    session: SubscribedSession,
    use_case: Annotated[SubmitRoleplayTurn, Depends(get_coach_turn_use_case)],
) -> TurnResponse:
    previous = tuple(PreviousTurn(t.parent, t.caregiver, t.score) for t in body.previous_turns)
    view = await use_case.execute(session, run_id, body.round, body.reply, previous)
    return turn_response(view)


@router.post("/{run_id}/finish", response_model=FinishResponse)
async def finish(
    run_id: UUID,
    session: SubscribedSession,
    use_case: Annotated[FinishRoleplay, Depends(_finish)],
    body: FinishRequest | None = None,
) -> FinishResponse:
    phrases = tuple(TurnPhrase(p.reply, p.better_phrase) for p in (body or FinishRequest()).phrases)
    return finish_response(await use_case.execute(session, run_id, phrases))
