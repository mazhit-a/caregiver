"""Lazy demo renewal: roll the period of a demo subscription whenever app time passes its end."""

from datetime import datetime, timedelta

from app.application.ports import ContentProvider, UnitOfWork
from app.domain.session.entities import Session

DEMO_RENEWED_EVENT = "demo_renewed"


class RollDemoRenewals:
    """While `app_now >= period_end`: renew by `renewDays` (a `canceling` demo ends instead).

    Runs inside the caller's open unit of work (session resolution), which commits. History
    entries are recorded at the period boundary that was crossed, in app time. Only demo
    subscriptions are rolled: Stripe renewals arrive through webhooks.
    """

    def __init__(self, uow: UnitOfWork, content: ContentProvider) -> None:
        self._uow = uow
        self._content = content

    async def execute(self, session: Session, app_now: datetime) -> None:
        subscription = await self._uow.subscriptions.get(session.id)
        if subscription is None or subscription.source != "demo":
            return
        if subscription.status not in ("demo", "canceling"):
            return
        changed = False
        while (
            subscription.current_period_end is not None
            and app_now >= subscription.current_period_end
        ):
            boundary = subscription.current_period_end
            if subscription.status == "canceling":
                subscription.end_period(boundary, "demo")
                changed = True
                break
            renew_days = self._content.pricing().plan(subscription.plan_id).renew_days
            subscription.renew(
                boundary, boundary + timedelta(days=renew_days), DEMO_RENEWED_EVENT, "demo"
            )
            changed = True
        if not changed:
            return
        await self._uow.subscriptions.save(subscription)
        for entry in subscription.pull_history():
            await self._uow.subscription_history.add(entry)
