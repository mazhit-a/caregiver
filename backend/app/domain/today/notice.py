"""The subscription notice on Today: renews on, renewed, or ends on. Never a payment-failed
notice: a `past_due` session is stopped by the access gate before Today is reached."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from app.domain.billing.entities import Subscription

NoticeKind = Literal["renews_on", "renewed", "ends_on"]


@dataclass(frozen=True)
class SubscriptionNotice:
    kind: NoticeKind
    on: date


def subscription_notice(
    subscription: Subscription, app_now: datetime, timezone: str, renewed_days: int
) -> SubscriptionNotice | None:
    """`canceling` -> ends on the period end. `active`/`demo` -> renewed (period start) when a
    renewal rolled within the last `renewed_days` days, else renews on the period end."""
    zone = ZoneInfo(timezone)
    end = subscription.current_period_end
    if end is None:
        return None
    if subscription.status == "canceling":
        return SubscriptionNotice("ends_on", end.astimezone(zone).date())
    if subscription.status not in ("active", "demo"):
        return None
    start = subscription.current_period_start
    if (
        subscription.renewal_count > 0
        and start is not None
        and timedelta(0) <= app_now - start < timedelta(days=renewed_days)
    ):
        return SubscriptionNotice("renewed", start.astimezone(zone).date())
    return SubscriptionNotice("renews_on", end.astimezone(zone).date())
