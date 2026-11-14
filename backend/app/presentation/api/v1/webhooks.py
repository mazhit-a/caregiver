"""Provider webhooks. Authenticated by signature, not by session token; not behind the gate."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.billing.stripe_events import HandleStripeEvent
from app.application.ports import Clock, ContentProvider, UnitOfWork, WebhookParser
from app.presentation.api.deps import get_clock, get_uow
from app.presentation.api.schemas.base import CamelModel

router = APIRouter(tags=["webhooks"])


class WebhookAck(CamelModel):
    received: bool


def _handle_stripe_event(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> HandleStripeEvent:
    content: ContentProvider = request.app.state.content
    return HandleStripeEvent(uow, content, clock)


@router.post("/webhooks/stripe", response_model=WebhookAck)
async def stripe_webhook(
    request: Request, handle: Annotated[HandleStripeEvent, Depends(_handle_stripe_event)]
) -> WebhookAck:
    """Verify the signature (400 when missing or wrong), then process the event once.

    Unknown event types and duplicates are acknowledged with 200.
    """
    parser: WebhookParser = request.app.state.webhook_parser
    event = parser.parse(await request.body(), request.headers.get("stripe-signature"))
    await handle.execute(event)
    return WebhookAck(received=True)
