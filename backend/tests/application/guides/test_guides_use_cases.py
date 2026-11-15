from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.guides.use_cases import GetGuide, ListGuides
from app.domain.guides.entities import UnknownGuide
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.fakes.clock import FixedClock

CONTENT = JsonContentProvider.from_directory(Path(__file__).resolve().parents[4] / "content")


def _session(key: str | None, name: str | None = None) -> Session:
    now = FixedClock().now()
    return Session(
        uuid4(), "h", "UTC", timedelta(0), now, now, recipient_key=key, display_name=name
    )


def test_list_without_a_session_uses_neutral_labels() -> None:
    guides = ListGuides(CONTENT).execute(None)
    assert [g.id for g in guides] == [
        "qg_missing",
        "qg_fall",
        "qg_sudden_change",
        "qg_hospital",
        "qg_limit",
    ]
    assert guides[0].title == "If your loved one goes missing"


def test_get_uses_the_session_labels() -> None:
    guide = GetGuide(CONTENT).execute("qg_fall", _session("dad"))
    assert guide.call_now[0] == "Dad hit Dad's head, or you're not sure"
    assert guide.footer == "In an emergency, call 911."


def test_both_becomes_the_singular_parent() -> None:
    guide = GetGuide(CONTENT).execute("qg_missing", _session("both"))
    assert guide.title == "If your parent goes missing"


def test_display_name_replaces_the_label() -> None:
    assert GetGuide(CONTENT).execute("qg_missing", _session("mom", "Rosa")).title == (
        "If Rosa goes missing"
    )


def test_unknown_guide_raises() -> None:
    with pytest.raises(UnknownGuide):
        GetGuide(CONTENT).execute("qg_nope", None)
