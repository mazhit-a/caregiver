from datetime import UTC, datetime, timedelta

from app.domain.today.checkins import checkin_due

CREATED = datetime(2026, 1, 5, 23, 30, tzinfo=UTC)


def test_checkin_not_due_on_same_app_day_and_due_next_day() -> None:
    assert not checkin_due(CREATED, CREATED, "UTC", has_checkin=False)
    assert not checkin_due(CREATED, CREATED + timedelta(minutes=20), "UTC", has_checkin=False)
    assert checkin_due(CREATED, CREATED + timedelta(hours=1), "UTC", has_checkin=False)


def test_due_uses_the_session_timezone_day_not_24_hours() -> None:
    # 23:30 UTC is 18:30 in New York; next New York day starts at 05:00 UTC
    assert not checkin_due(CREATED, CREATED + timedelta(hours=5), "America/New_York", False)
    assert checkin_due(CREATED, CREATED + timedelta(hours=6), "America/New_York", False)


def test_not_due_once_answered() -> None:
    assert not checkin_due(CREATED, CREATED + timedelta(days=2), "UTC", has_checkin=True)
