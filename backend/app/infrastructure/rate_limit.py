"""In-memory sliding-window rate limiter (per process; enough for a single-instance demo)."""

from collections import defaultdict, deque
from datetime import datetime, timedelta


class InMemoryRateLimiter:
    """At most `limit` hits per `window` for each key; time comes from the caller's clock."""

    def __init__(self, limit: int, window: timedelta = timedelta(hours=1)) -> None:
        self._limit = limit
        self._window = window
        self._hits: defaultdict[str, deque[datetime]] = defaultdict(deque)

    async def allow(self, key: str, now: datetime) -> bool:
        hits = self._hits[key]
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True
