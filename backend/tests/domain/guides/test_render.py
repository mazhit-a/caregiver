import pytest

from app.domain.guides.entities import (
    GuideCommon,
    GuideResource,
    GuideSource,
    GuideStep,
    QuickGuide,
    QuickGuideBook,
    UnknownGuide,
)
from app.domain.guides.render import render_guide
from app.domain.shared.labels import RecipientLabels

DAD = RecipientLabels("Dad", "Dad's", "he", "him", "was", "is", "has", "lives")

GUIDE = QuickGuide(
    id="qg_x",
    title="If {recipient} falls",
    summary="Check {object}.",
    urgency="emergency",
    call_now=("{Pronoun} hit {possessive} head",),
    steps=(GuideStep("Look at {object}", "{Recipient} may be hurt."),),
    then=("Tell {possessive} doctor.",),
    dont=("Don't lift {object}.",),
    resources=("911",),
    sources=(GuideSource("Src", "https://example.org"),),
)
BOOK = QuickGuideBook(
    common=GuideCommon("Footer.", "Call 911 now if", "What to do", "Then", "Don't", "Who can help"),
    resources={"911": GuideResource("Emergency", "911", "911")},
    guides=(GUIDE,),
)


def test_render_fills_every_placeholder_and_resolves_resources() -> None:
    r = render_guide(BOOK, GUIDE, DAD)
    assert r.title == "If Dad falls"
    assert r.call_now == ("He hit Dad's head",)
    assert r.steps[0] == GuideStep("Look at him", "Dad may be hurt.")
    assert r.then == ("Tell Dad's doctor.",)
    assert r.dont == ("Don't lift him.",)
    assert r.resources == (GuideResource("Emergency", "911", "911"),)
    assert r.footer == "Footer."
    assert r.call_now_title == "Call 911 now if"


def test_get_unknown_guide_raises_with_the_id() -> None:
    with pytest.raises(UnknownGuide) as exc:
        BOOK.get("nope")
    assert exc.value.code == "unknown_guide"
    assert BOOK.get("qg_x") is GUIDE
