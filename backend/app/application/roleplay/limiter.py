"""Process-wide cap on concurrent LLM calls. It never queues: a full limiter says no at once."""

DEFAULT_MAX_IN_FLIGHT = 4


class LlmConcurrencyLimiter:
    """Non-blocking counter. One instance per process, wired in the composition root."""

    def __init__(self, max_in_flight: int = DEFAULT_MAX_IN_FLIGHT) -> None:
        self._max = max_in_flight
        self._in_flight = 0

    @property
    def in_flight(self) -> int:
        return self._in_flight

    def try_acquire(self) -> bool:
        if self._in_flight >= self._max:
            return False
        self._in_flight += 1
        return True

    def release(self) -> None:
        self._in_flight = max(0, self._in_flight - 1)
