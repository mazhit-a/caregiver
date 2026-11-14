"""Demo-controls response schema."""

from datetime import date, datetime

from app.presentation.api.schemas.base import CamelModel

DEMO_LABEL = "Demo controls: simulated time, not real time."


class DemoResponse(CamelModel):
    demo_controls: bool = True
    label: str = DEMO_LABEL
    app_now: datetime
    app_today: date
    clock_offset_seconds: int
    subscription_status: str
    current_period_end: datetime | None
    renewal_count: int
    billing_sync: str  # none | pending | done
