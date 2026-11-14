"""Clock adapters: the system clock and the session-offset app clock."""

from datetime import UTC, datetime, timedelta

from app.application.ports import Clock


class SystemClock:
    """Real UTC now. The only place (with tokens.py) that reads the wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class AppClock:
    """App time: a base clock plus a session offset (demo time travel)."""

    def __init__(self, base: Clock, offset: timedelta) -> None:
        self._base = base
        self._offset = offset

    def now(self) -> datetime:
        return self._base.now() + self._offset
