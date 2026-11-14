"""Demo-controls DTOs."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.domain.billing.entities import BillingSync, SubscriptionStatus


@dataclass(frozen=True)
class DemoState:
    """The session's app clock and subscription period, as the demo panel shows them."""

    app_now: datetime
    app_today: date
    clock_offset: timedelta
    subscription_status: SubscriptionStatus
    current_period_end: datetime | None
    renewal_count: int
    billing_sync: BillingSync
