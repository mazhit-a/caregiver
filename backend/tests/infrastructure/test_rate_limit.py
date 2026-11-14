from datetime import UTC, datetime, timedelta

from app.application.roleplay.limiter import LlmConcurrencyLimiter
from app.infrastructure.rate_limit import InMemoryRateLimiter

NOW = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)


async def test_window_slides_and_keys_are_independent() -> None:
    limiter = InMemoryRateLimiter(2)
    assert await limiter.allow("a", NOW) and await limiter.allow("a", NOW)
    assert not await limiter.allow("a", NOW + timedelta(minutes=59))
    assert await limiter.allow("b", NOW)
    assert await limiter.allow("a", NOW + timedelta(hours=1))


def test_llm_limiter_never_queues_and_release_frees_a_slot() -> None:
    limiter = LlmConcurrencyLimiter(2)
    assert limiter.try_acquire() and limiter.try_acquire() and not limiter.try_acquire()
    limiter.release()
    assert limiter.try_acquire() and limiter.in_flight == 2
