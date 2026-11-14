import pytest

from app.domain.events.catalog import EVENT_PROPS, UnknownEvent, clean_event


def test_every_funnel_qa_event_name_is_in_the_catalog() -> None:
    funnel = {
        "landing_view", "quiz_start", "quiz_answer", "quiz_back", "quiz_complete", "plan_built",
        "plan_preview_view", "gift_download", "paywall_view", "plan_selected", "consent_checked",
        "checkout_start", "checkout_success", "checkout_canceled", "demo_mode", "save_plan",
        "lesson_start",
    }  # fmt: skip
    app = {"lesson_complete", "roleplay_finish", "checkin_answer", "card_published",
           "demo_next_day", "renewed"}  # fmt: skip
    assert funnel | app <= set(EVENT_PROPS)


def test_unknown_name_raises() -> None:
    with pytest.raises(UnknownEvent):
        clean_event("rm_rf", {})


def test_props_outside_the_whitelist_or_of_the_wrong_kind_are_dropped() -> None:
    event = clean_event(
        "quiz_answer", {"questionId": "q3", "value": "dementia", "answer": ["a"], "x": 1}
    )
    assert event.props == {"questionId": "q3"}
    assert clean_event("plan_built", {"itemsCount": True, "rulesVersion": "v1"}).props == {
        "rulesVersion": "v1"
    }
    assert clean_event("save_plan", {"skipped": "yes"}).props == {}


def test_free_text_strings_are_dropped_even_on_a_whitelisted_prop() -> None:
    assert clean_event("quiz_answer", {"questionId": "She forgets my name"}).props == {}
    assert clean_event("quiz_answer", {"questionId": "x" * 41}).props == {}
    assert clean_event("landing_view", {"source": "newsletter"}).props == {"source": "newsletter"}
