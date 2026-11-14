"""The anonymous session and its app clock (real now + offset, in the session timezone)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.session.errors import InvalidTimezone

DEFAULT_TIMEZONE = "America/New_York"


def validate_timezone(name: str) -> ZoneInfo:
    """Return the zone for an IANA name or raise InvalidTimezone."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise InvalidTimezone("Unknown IANA timezone.", {"timezone": name}) from exc


@dataclass
class Session:
    id: UUID
    token_hash: str
    timezone: str
    clock_offset: timedelta
    created_at: datetime
    last_seen_at: datetime
    recipient_key: str | None = None
    display_name: str | None = None

    def app_now(self, real_now: datetime) -> datetime:
        """App time: real now plus the session offset (zero in normal use)."""
        return real_now + self.clock_offset

    def app_today(self, real_now: datetime) -> date:
        """The app date in the session timezone."""
        return self.app_now(real_now).astimezone(ZoneInfo(self.timezone)).date()

    def touch(self, real_now: datetime) -> None:
        self.last_seen_at = self.app_now(real_now)
