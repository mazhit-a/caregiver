"""FastAPI dependencies: settings access now; auth, gate and use-case factories later."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from app.application.billing.use_cases import CheckAccess
from app.application.demo.renewals import RollDemoRenewals
from app.application.ports import (
    Clock,
    ContentProvider,
    IdGenerator,
    PaymentGateway,
    TokenGenerator,
    UnitOfWork,
)
from app.application.session.use_cases import CreateSession, ResolveSession
from app.domain.billing.errors import PaymentGatewayError
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


def get_payment_gateway(request: Request) -> PaymentGateway:
    """The payment gateway, or `PaymentGatewayError` (502, demo hint) when Stripe is not set up."""
    gateway: PaymentGateway | None = request.app.state.payment_gateway
    if gateway is None:
        raise PaymentGatewayError("Card payments are not configured on this server.")
    return gateway


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
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> ResolveSession:
    # Content is loaded by the lifespan; without it (bare test apps) no renewal can roll.
    content: ContentProvider | None = getattr(request.app.state, "content", None)
    roll = RollDemoRenewals(uow, content) if content is not None else None
    return ResolveSession(uow, clock, roll)


async def get_current_session(
    resolve: Annotated[ResolveSession, Depends(get_resolve_session)],
    x_session_token: Annotated[str | None, Header()] = None,
) -> Session:
    """Authenticate by `X-Session-Token`; touches last_seen_at and records the app day."""
    return await resolve.execute(x_session_token)


CurrentSession = Annotated[Session, Depends(get_current_session)]


# --- access gate ---


def get_check_access(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> CheckAccess:
    return CheckAccess(uow, clock)


async def require_subscription(
    session: CurrentSession, check: Annotated[CheckAccess, Depends(get_check_access)]
) -> Session:
    """The access gate: authenticates, then asks `Subscription.can_access()`.

    Raises `AccessDenied` (402, `details.reason` = no_plan | no_subscription | past_due | ended).
    """
    await check.execute(session)
    return session


SubscribedSession = Annotated[Session, Depends(require_subscription)]
"""Use as the session parameter of every gated app route (instead of `CurrentSession`)."""


# --- demo controls guard ---


def require_demo_controls(info: AppInfoDep) -> None:
    """404 in the shared error shape unless `DEMO_CONTROLS=true` (the routes look absent)."""
    if not info.demo_controls:
        raise HTTPException(status_code=404, detail="Not Found")
