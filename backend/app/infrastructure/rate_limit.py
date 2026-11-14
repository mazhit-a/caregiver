"""In-memory sliding-window rate limiter: the `RateLimiter` port for ONE process.

Counters live in this process's memory. That is correct only with a single uvicorn worker (the
Dockerfile runs one); with several workers every limit would multiply. To scale out, add another
implementation of the `RateLimiter` port (for example Redis) and wire it in `main.py`.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta

_SWEEP_EVERY = 1024  # calls between sweeps of keys whose window has fully expired


class InMemoryRateLimiter:
    """At most `limit` hits per `window` for each key; time comes from the caller's clock."""

    def __init__(self, limit: int, window: timedelta = timedelta(hours=1)) -> None:
        self._limit = limit
        self._window = window
        self._hits: defaultdict[str, deque[datetime]] = defaultdict(deque)
        self._calls = 0

    async def allow(self, key: str, now: datetime) -> bool:
        self._calls += 1
        if self._calls % _SWEEP_EVERY == 0:
            self._sweep(now)
        hits = self._hits[key]
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True

    def _sweep(self, now: datetime) -> None:
        """Drop idle keys so per-client keys cannot grow memory without bound."""
        cutoff = now - self._window
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]:
            del self._hits[key]

    @property
    def tracked_keys(self) -> int:
        return len(self._hits)
