"""FastAPI dependencies: settings access now; auth, gate and use-case factories later."""

from typing import Annotated

from fastapi import Depends, Header, Request

from app.application.ports import Clock, IdGenerator, TokenGenerator, UnitOfWork
from app.application.session.use_cases import CreateSession, ResolveSession
from app.domain.session.entities import Session
from app.presentation.api.schemas.base import CamelModel


class AppInfo(CamelModel):
    """Non-secret settings the presentation layer may read."""

    demo_controls: bool


def get_app_info(request: Request) -> AppInfo:
    info: AppInfo = request.app.state.app_info
    return info


AppInfoDep = Annotated[AppInfo, Depends(get_app_info)]


# --- sessions: use-case factories and token auth -------------------------------------------------


def get_uow(request: Request) -> UnitOfWork:
    uow: UnitOfWork = request.app.state.uow_factory()
    return uow


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_token_generator(request: Request) -> TokenGenerator:
    tokens: TokenGenerator = request.app.state.token_generator
    return tokens


def get_id_generator(request: Request) -> IdGenerator:
    ids: IdGenerator = request.app.state.id_generator
    return ids


def get_create_session(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    tokens: Annotated[TokenGenerator, Depends(get_token_generator)],
    ids: Annotated[IdGenerator, Depends(get_id_generator)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> CreateSession:
    return CreateSession(uow, tokens, ids, clock)


def get_resolve_session(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> ResolveSession:
    return ResolveSession(uow, clock)


async def get_current_session(
    resolve: Annotated[ResolveSession, Depends(get_resolve_session)],
    x_session_token: Annotated[str | None, Header()] = None,
) -> Session:
    """Authenticate by `X-Session-Token`; touches last_seen_at and records the app day."""
    return await resolve.execute(x_session_token)


CurrentSession = Annotated[Session, Depends(get_current_session)]
