"""Care card routes. The session routes sit behind the access gate; the public route
`GET /cards/{id}` needs no session, is rate-limited per client and never cached. Neither logs
card text (the access log writes method, path and status only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.application.care_card.use_cases import (
    GetCareCard,
    GetPublicCard,
    PublishCareCard,
    RevokeCareCard,
    UpdateCareCard,
)
from app.application.ports import Clock, ContentProvider, RateLimiter, TokenGenerator, UnitOfWork
from app.presentation.api.deps import (
    SubscribedSession,
    get_clock,
    get_token_generator,
    get_uow,
)
from app.presentation.api.roleplay_deps import get_content
from app.presentation.api.schemas.care_card import (
    CardSnapshotOut,
    CareCardRequest,
    CareCardResponse,
    care_card_response,
    snapshot_out,
)

router = APIRouter(tags=["care-card"])

Uow = Annotated[UnitOfWork, Depends(get_uow)]
Content = Annotated[ContentProvider, Depends(get_content)]
Clk = Annotated[Clock, Depends(get_clock)]


def _get(uow: Uow, content: Content, clock: Clk) -> GetCareCard:
    return GetCareCard(uow, content, clock)


def _publish(
    uow: Uow,
    content: Content,
    clock: Clk,
    tokens: Annotated[TokenGenerator, Depends(get_token_generator)],
) -> PublishCareCard:
    return PublishCareCard(uow, content, clock, tokens)


def _update(uow: Uow, content: Content, clock: Clk) -> UpdateCareCard:
    return UpdateCareCard(uow, content, clock)


def _revoke(uow: Uow, clock: Clk) -> RevokeCareCard:
    return RevokeCareCard(uow, clock)


def _public(request: Request, uow: Uow, clock: Clk) -> GetPublicCard:
    limiter: RateLimiter = request.app.state.card_rate_limiter
    return GetPublicCard(uow, clock, limiter)


def _public_url(request: Request) -> str:
    url: str = request.app.state.settings.public_app_url
    return url


def _client_key(request: Request) -> str:
    """The caller: the last X-Forwarded-For hop (appended by our own proxy), else the peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@router.get("/care-card", response_model=CareCardResponse)
async def get_care_card(
    request: Request, session: SubscribedSession, use_case: Annotated[GetCareCard, Depends(_get)]
) -> CareCardResponse:
    return care_card_response(await use_case.execute(session), _public_url(request))


@router.post("/care-card", response_model=CareCardResponse)
async def publish_care_card(
    request: Request,
    body: CareCardRequest,
    session: SubscribedSession,
    publish: Annotated[PublishCareCard, Depends(_publish)],
    view: Annotated[GetCareCard, Depends(_get)],
) -> CareCardResponse:
    await publish.execute(session, body.phrase_ids)
    return care_card_response(await view.execute(session), _public_url(request))


@router.put("/care-card", response_model=CareCardResponse)
async def update_care_card(
    request: Request,
    body: CareCardRequest,
    session: SubscribedSession,
    update: Annotated[UpdateCareCard, Depends(_update)],
    view: Annotated[GetCareCard, Depends(_get)],
) -> CareCardResponse:
    await update.execute(session, body.phrase_ids)
    return care_card_response(await view.execute(session), _public_url(request))


@router.delete("/care-card", response_model=CareCardResponse)
async def revoke_care_card(
    request: Request,
    session: SubscribedSession,
    revoke: Annotated[RevokeCareCard, Depends(_revoke)],
    view: Annotated[GetCareCard, Depends(_get)],
) -> CareCardResponse:
    await revoke.execute(session)
    return care_card_response(await view.execute(session), _public_url(request))


@router.get("/cards/{card_id}", response_model=CardSnapshotOut)
async def get_public_card(
    card_id: str,
    request: Request,
    response: Response,
    use_case: Annotated[GetPublicCard, Depends(_public)],
) -> CardSnapshotOut:
    response.headers["Cache-Control"] = "no-store"
    return snapshot_out(await use_case.execute(card_id, _client_key(request)))
