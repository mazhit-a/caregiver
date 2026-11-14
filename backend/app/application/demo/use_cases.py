"""Demo controls: read the app clock, simulate the next day, jump to the renewal."""

from datetime import timedelta

from app.application.demo.dto import DemoState
from app.application.ports import Clock, UnitOfWork
from app.domain.billing.entities import Subscription
from app.domain.billing.errors import NoSubscriptionPeriod
from app.domain.session.entities import Session

_ONE_DAY = timedelta(hours=24)
_AFTER_RENEWAL = timedelta(hours=1)
_LIVE_STATUSES = ("demo", "active", "canceling", "past_due")


def _state(session: Session, subscription: Subscription, clock: Clock) -> DemoState:
    real_now = clock.now()
    return DemoState(
        app_now=session.app_now(real_now),
        app_today=session.app_today(real_now),
        clock_offset=session.clock_offset,
        subscription_status=subscription.status,
        current_period_end=subscription.current_period_end,
        renewal_count=subscription.renewal_count,
    )


class GetDemoState:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session) -> DemoState:
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
        return _state(session, subscription, self._clock)


class AdvanceDemoDay:
    """`next-day`: the session's clock offset grows by 24 hours."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session) -> DemoState:
        session.clock_offset += _ONE_DAY
        async with self._uow:
            await self._uow.sessions.save(session)
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            await self._uow.commit()
        return _state(session, subscription, self._clock)


class JumpToRenewal:
    """`jump-to-renewal`: offset so that `app_now` is one hour after the current period end.

    The renewal itself rolls lazily on the next request (see `RollDemoRenewals`).
    """

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, session: Session) -> DemoState:
        async with self._uow:
            subscription = await self._uow.subscriptions.get(session.id) or Subscription(session.id)
            period_end = subscription.current_period_end
            if period_end is None or subscription.status not in _LIVE_STATUSES:
                raise NoSubscriptionPeriod()
            session.clock_offset = period_end + _AFTER_RENEWAL - self._clock.now()
            await self._uow.sessions.save(session)
            await self._uow.commit()
        return _state(session, subscription, self._clock)
