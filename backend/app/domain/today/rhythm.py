"""Weekly rhythm (Monday to Sunday in the session timezone) and the welcome-back rule."""

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def week_bounds(today: date) -> tuple[date, date]:
    """The Monday and the Sunday of the week that contains `today`."""
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def sessions_this_week(finished_at: Iterable[datetime], today: date, timezone: str) -> int:
    """How many of the finished times fall on a day of this Monday-Sunday week (local days)."""
    zone = ZoneInfo(timezone)
    monday, sunday = week_bounds(today)
    return sum(1 for at in finished_at if monday <= at.astimezone(zone).date() <= sunday)


def is_welcome_back(previous_seen: datetime | None, app_now: datetime, after_days: int) -> bool:
    """True when the previous visit was at least `after_days` days before app time now."""
    return previous_seen is not None and app_now - previous_seen >= timedelta(days=after_days)
