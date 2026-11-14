from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from app.domain.billing.entities import Subscription
from app.domain.today.notice import subscription_notice
from app.domain.today.rhythm import is_welcome_back, sessions_this_week, week_bounds

NOW = datetime(2026, 1, 7, 12, 0, tzinfo=UTC)


def test_week_runs_monday_to_sunday() -> None:
    assert week_bounds(date(2026, 1, 7)) == (date(2026, 1, 5), date(2026, 1, 11))
    assert week_bounds(date(2026, 1, 5)) == (date(2026, 1, 5), date(2026, 1, 11))
    assert week_bounds(date(2026, 1, 11)) == (date(2026, 1, 5), date(2026, 1, 11))


def test_weekly_rhythm_uses_monday_to_sunday_in_session_timezone() -> None:
    # 2026-01-12 03:00 UTC is still Sunday 22:00 in New York: last week there, this week in UTC.
    late_sunday_ny = datetime(2026, 1, 12, 3, 0, tzinfo=UTC)
    new_york_sunday = date(2026, 1, 11)
    assert sessions_this_week([late_sunday_ny], new_york_sunday, "America/New_York") == 1
    assert sessions_this_week([late_sunday_ny], date(2026, 1, 12), "America/New_York") == 0
    assert sessions_this_week([late_sunday_ny], date(2026, 1, 12), "UTC") == 1
    last_sunday = datetime(2026, 1, 4, 23, 0, tzinfo=UTC)
    assert sessions_this_week([last_sunday], date(2026, 1, 7), "UTC") == 0


def test_welcome_back_needs_a_previous_visit_at_least_7_days_ago() -> None:
    assert not is_welcome_back(None, NOW, 7)
    assert not is_welcome_back(NOW - timedelta(days=6, hours=23), NOW, 7)
    assert is_welcome_back(NOW - timedelta(days=7), NOW, 7)


def _subscription(status: str, renewals: int, start: datetime, end: datetime) -> Subscription:
    return Subscription(
        uuid4(),
        status=status,  # type: ignore[arg-type]
        current_period_start=start,
        current_period_end=end,
        renewal_count=renewals,
    )


def test_subscription_notice_variants() -> None:
    start = NOW - timedelta(days=1)
    end = NOW + timedelta(days=6)
    renews = subscription_notice(_subscription("demo", 0, start, end), NOW, "UTC", 7)
    assert renews is not None and (renews.kind, renews.on) == ("renews_on", date(2026, 1, 13))
    renewed = subscription_notice(_subscription("active", 1, start, end), NOW, "UTC", 7)
    assert renewed is not None and (renewed.kind, renewed.on) == ("renewed", date(2026, 1, 6))
    old = NOW - timedelta(days=10)
    later = subscription_notice(_subscription("active", 1, old, end), NOW, "UTC", 7)
    assert later is not None and later.kind == "renews_on"
    ends = subscription_notice(_subscription("canceling", 0, start, end), NOW, "UTC", 7)
    assert ends is not None and (ends.kind, ends.on) == ("ends_on", date(2026, 1, 13))


def test_no_notice_for_states_that_cannot_reach_today() -> None:
    for status in ("none", "past_due", "canceled", "ended"):
        assert subscription_notice(_subscription(status, 0, NOW, NOW), NOW, "UTC", 7) is None
