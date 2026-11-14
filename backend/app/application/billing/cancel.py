"""Cancel preview ("what you'd lose") and cancel at period end. No offers, no discounts."""

from dataclasses import dataclass
from datetime import datetime

from app.application.ports import Clock, ContentProvider, PaymentGateway, UnitOfWork
from app.domain.billing.entities import Subscription
from app.domain.billing.errors import NoActiveSubscription, PaymentGatewayError
from app.domain.session.entities import Session

# Statuses a preview can be shown for; only the first two can actually be canceled.
_PREVIEW_STATUSES = ("active", "demo", "past_due", "canceling")
_CANCELABLE_STATUSES = ("active", "demo")


@dataclass(frozen=True)
class CancelPreview:
    plan_name: str
    saved_phrase_count: int
    care_card_published: bool
    end_date: datetime | None  # access continues until then (the end of the paid period)
    status: str


@dataclass(frozen=True)
class CancelResult:
    status: str
    end_date: datetime | None


class GetCancelPreview:
    def __init__(self, uow: UnitOfWork, content: ContentProvider) -> None:
        self._uow = uow
        self._content = content

    async def execute(self, session: Session) -> CancelPreview:
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            if subscription.status not in _PREVIEW_STATUSES:
                raise NoActiveSubscription(subscription.status)
            phrases = await self._uow.saved_phrases.count(session.id)
            card = await self._uow.care_cards.get_current(session.id)
        plan = self._content.pricing().plan(subscription.plan_id)
        return CancelPreview(
            plan_name=plan.label,
            saved_phrase_count=phrases,
            care_card_published=card is not None and not card.is_revoked,
            end_date=subscription.current_period_end,
            status=subscription.status,
        )


class CancelSubscription:
    """`POST /api/billing/cancel`: cancel at the end of the paid period; access continues.

    A Stripe subscription is canceled at Stripe first (`cancel_at_period_end`); when that fails
    the error is raised and nothing changes here. A demo subscription only changes status; the
    lazy demo renewal ends it at the period end.
    """

    def __init__(self, uow: UnitOfWork, clock: Clock, gateway: PaymentGateway | None) -> None:
        self._uow = uow
        self._clock = clock
        self._gateway = gateway

    async def execute(self, session: Session) -> CancelResult:
        now = session.app_now(self._clock.now())
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
        if subscription.status not in _CANCELABLE_STATUSES:
            raise NoActiveSubscription(subscription.status)
        if subscription.source == "stripe":
            if self._gateway is None or subscription.stripe_subscription_id is None:
                raise PaymentGatewayError("Card payments are not configured on this server.")
            await self._gateway.cancel_at_period_end(subscription.stripe_subscription_id)
        async with self._uow:
            # Re-read: the `customer.subscription.updated` webhook may have changed it meanwhile.
            current = await self._uow.subscriptions.get(session.id) or subscription
            if current.status in _CANCELABLE_STATUSES:
                current.cancel_at_period_end(now, current.source)
                await self._uow.subscriptions.save(current)
                for entry in current.pull_history():
                    await self._uow.subscription_history.add(entry)
                await self._uow.commit()
        return CancelResult("canceling", current.current_period_end)
