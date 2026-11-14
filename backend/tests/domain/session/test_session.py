from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.session.entities import Session, validate_timezone
from app.domain.session.errors import InvalidTimezone
from app.domain.session.tokens import hash_token

NY = "America/New_York"


def make_session(offset: timedelta = timedelta(0), tz: str = NY) -> Session:
    now = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    return Session(
        id=UUID(int=1),
        token_hash="h",
        timezone=tz,
        clock_offset=offset,
        created_at=now,
        last_seen_at=now,
    )


def test_app_today_uses_session_timezone_and_offset() -> None:
    # 23:30 on 5 Jan in New York is 04:30 UTC on 6 Jan.
    real_now = datetime(2026, 1, 6, 4, 30, tzinfo=UTC)
    assert make_session().app_today(real_now).isoformat() == "2026-01-05"
    shifted = make_session(offset=timedelta(hours=24))
    assert shifted.app_today(real_now).isoformat() == "2026-01-06"
    # Same instant, another zone: the date depends on the session timezone.
    assert make_session(tz="Asia/Tokyo").app_today(real_now).isoformat() == "2026-01-06"


def test_touch_stores_app_time_not_real_time() -> None:
    session = make_session(offset=timedelta(hours=24))
    real_now = datetime(2026, 1, 6, 4, 30, tzinfo=UTC)
    session.touch(real_now)
    assert session.last_seen_at == real_now + timedelta(hours=24)


def test_hash_token_is_sha256_hex_and_deterministic() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert len(hash_token("abc")) == 64
    assert hash_token("abc") != "abc"


def test_validate_timezone_accepts_iana_and_rejects_unknown() -> None:
    assert str(validate_timezone("Europe/Berlin")) == "Europe/Berlin"
    for bad in ("Mars/Olympus", "", "../etc/passwd", "EST5EDT5"):
        with pytest.raises(InvalidTimezone):
            validate_timezone(bad)
