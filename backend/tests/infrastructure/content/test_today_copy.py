import re

from app.infrastructure.content.provider import JsonContentProvider
from tests.infrastructure.content.test_loader import REAL_CONTENT

KNOWN_PLACEHOLDERS = {
    "recipient",
    "Recipient",
    "possessive",
    "Possessive",
    "date",
    "count",
    "done",
    "target",
    "total",
}


def test_today_copy_loads_from_funnel_copy_with_the_agreed_wording() -> None:
    copy = JsonContentProvider.from_directory(REAL_CONTENT).today_copy()
    assert copy.rest_message == "You're done for today. Rest counts too."
    assert copy.care_card_nudge_one == "Your care card has 1 new phrase. Update it?"
    assert copy.welcome_back_after_days == 7 and copy.renewed_notice_days >= 1
    assert [c.id for c in copy.demo_controls] == ["nextDay", "jumpToRenewal"]
    assert "Simulate next day" in copy.demo_controls[0].label


def test_today_copy_uses_only_known_placeholders() -> None:
    copy = JsonContentProvider.from_directory(REAL_CONTENT).today_copy()
    for value in vars(copy).values():
        if isinstance(value, str):
            assert set(re.findall(r"\{(\w+)\}", value)) <= KNOWN_PLACEHOLDERS, value
