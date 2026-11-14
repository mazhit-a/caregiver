"""Gentle exit and "Clear my data": end the subscription, then delete everything.

One erasing routine (`EraseSession`) serves both. A card subscription is canceled at the provider
first and immediately; when that fails nothing is changed or deleted and `BillingCancelFailed`
(retryable) is raised. Everything else relies on `ON DELETE CASCADE` from the session row.
No retention message of any kind lives here or in the wording it returns.
"""

from contextlib import suppress
from datetime import datetime

from app.application.care_card.use_cases import RevokeCareCard
from app.application.ports import Clock, ContentProvider, PaymentGateway, UnitOfWork
from app.domain.billing.entities import Subscription
from app.domain.billing.errors import BillingCancelFailed, PaymentGatewayError
from app.domain.billing.exit_copy import GentleExitCopy
from app.domain.care_card.errors import CardNotPublished
from app.domain.session.entities import Session

# A demo subscription has no provider side; these Stripe statuses still have a live subscription.
_LIVE_AT_PROVIDER = ("active", "past_due", "canceling")


class EraseSession:
    def __init__(self, uow: UnitOfWork, clock: Clock, gateway: PaymentGateway | None) -> None:
        self._uow = uow
        self._clock = clock
        self._gateway = gateway

    async def execute(self, session: Session) -> None:
        now = session.app_now(self._clock.now())
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id)
        if subscription is not None:
            await self._cancel_at_provider(subscription)
            await self._end(subscription, now)
        with suppress(CardNotPublished):
            await RevokeCareCard(self._uow, self._clock).execute(session)
        async with self._uow:
            await self._uow.sessions.delete(session.id)
            await self._uow.commit()

    async def _cancel_at_provider(self, subscription: Subscription) -> None:
        if subscription.source != "stripe" or subscription.status not in _LIVE_AT_PROVIDER:
            return
        if self._gateway is None or subscription.stripe_subscription_id is None:
            raise BillingCancelFailed()
        try:
            await self._gateway.cancel_now(subscription.stripe_subscription_id)
        except PaymentGatewayError as error:
            raise BillingCancelFailed() from error

    async def _end(self, subscription: Subscription, now: datetime) -> None:
        if subscription.status == "ended":
            return
        subscription.end_now(now, subscription.source)
        async with self._uow:
            await self._uow.subscriptions.save(subscription)
            for entry in subscription.pull_history():
                await self._uow.subscription_history.add(entry)
            await self._uow.commit()


class GentleExit:
    def __init__(self, erase: EraseSession, content: ContentProvider) -> None:
        self._erase = erase
        self._content = content

    async def execute(self, session: Session) -> GentleExitCopy:
        await self._erase.execute(session)
        return self._content.gentle_exit_copy()


class ClearMyData:
    def __init__(self, erase: EraseSession, content: ContentProvider) -> None:
        self._erase = erase
        self._content = content

    async def execute(self, session: Session) -> str:
        await self._erase.execute(session)
        return self._content.gentle_exit_copy().clear_data_confirmation
