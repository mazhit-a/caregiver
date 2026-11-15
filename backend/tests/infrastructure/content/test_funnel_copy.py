import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.funnel.render import (
    FunnelCopyView,
    TextSegment,
    render_funnel_copy,
    split_bold,
)
from app.infrastructure.content.provider import JsonContentProvider

REAL_CONTENT = Path(__file__).resolve().parents[4] / "content"
TODAY = date(2026, 11, 15)
HEARD = ("You are caring for Mom from far away.", "Evenings are hardest.")


def _strings(view: FunnelCopyView) -> list[str]:
    out = [
        view.loader_title,
        view.plan_preview_title,
        view.plan_preview_cta,
        view.highlight_label,
        view.health_note,
        view.paywall_headline,
        view.paywall_subhead,
        view.paywall_consent_required_error,
        view.paywall_success,
        view.paywall_returned_canceled,
        *view.paywall_includes,
    ]
    for p in view.plans:
        out += [p.label, p.price_today, p.detail, p.consent_label, p.pay_button_label]
        out += [s.text for s in p.disclosure]
    return out


@pytest.mark.parametrize("key", JsonContentProvider.from_directory(REAL_CONTENT).recipient_keys())
def test_every_recipient_key_renders_without_placeholders_or_markdown(key: str) -> None:
    content = JsonContentProvider.from_directory(REAL_CONTENT)
    view = render_funnel_copy(
        content.funnel_copy(), content.pricing(), content.recipient_labels(key), HEARD, TODAY
    )
    for text in _strings(view):
        assert text and "{" not in text and "}" not in text and "**" not in text
    assert view.paywall_subhead == HEARD[0]


def test_money_and_dates_come_from_pricing_json_and_the_given_day() -> None:
    content = JsonContentProvider.from_directory(REAL_CONTENT)
    raw = json.loads((REAL_CONTENT / "pricing.json").read_text())
    view = render_funnel_copy(
        content.funnel_copy(), content.pricing(), content.recipient_labels("mom"), HEARD, TODAY
    )
    assert view.default_plan_id == raw["defaultPlanId"]
    assert [p.id for p in view.plans] == [p["id"] for p in raw["plans"]]
    four = view.plans[0]
    assert four.price_today == "$19.99"
    assert four.detail == "for the first 4 weeks, then $39.99 every 4 weeks"
    assert four.first_renewal_date == "Dec 13"  # 2026-11-15 + 28 days
    assert four.pay_button_label == "Pay $19.99 and start"
    assert "$39.99" in four.consent_label and "agree" in four.consent_label
    assert view.plans[1].price_today == "$49.99" and view.plans[1].first_renewal_date == "Feb 7"
    assert view.paywall_headline == "Mom's 30-day plan is ready"
    # No price per day anywhere.
    assert not any("per day" in t or "/day" in t for t in _strings(view))


def test_disclosure_segments_mark_the_bold_parts() -> None:
    content = JsonContentProvider.from_directory(REAL_CONTENT)
    view = render_funnel_copy(
        content.funnel_copy(), content.pricing(), content.recipient_labels("mom"), HEARD, TODAY
    )
    segments = view.plans[0].disclosure
    assert segments[0] == TextSegment("Today: $19.99", strong=True)
    assert [s.strong for s in segments] == [True, False, True, False]
    text = "".join(s.text for s in segments)
    assert text.endswith("Cancel anytime in Settings → Manage my plan.")


def test_split_bold_plain_text_is_one_weak_segment() -> None:
    assert split_bold("plain") == (TextSegment("plain", strong=False),)
    assert split_bold("a **b** c") == (
        TextSegment("a ", strong=False),
        TextSegment("b", strong=True),
        TextSegment(" c", strong=False),
    )


def test_money_uses_decimal_with_two_places() -> None:
    from app.domain.funnel.render import format_money

    assert format_money(Decimal("29.9"), "${amount}") == "$29.90"
