from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.domain.quiz.definition import QuizDefinition
from app.domain.quiz.derived import parse_derived_rule
from app.domain.quiz.entities import QuizState
from app.domain.quiz.errors import InvalidAnswer, QuizLocked, QuizRuleError, UnknownQuestion
from app.domain.quiz.tags import derive
from app.infrastructure.content.loader import load_content
from app.infrastructure.content.quiz_mapper import to_quiz_definition

REPO = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def definition() -> QuizDefinition:
    return to_quiz_definition(load_content(REPO / "content").quiz)


def _state(definition: QuizDefinition, answers: dict[str, Any]) -> QuizState:
    state = QuizState(uuid4())
    for question_id, value in answers.items():
        state.answer(definition, question_id, value)
    return state


def test_multi_over_max_rejected(definition: QuizDefinition) -> None:
    with pytest.raises(InvalidAnswer):
        _state(definition, {"q5_changes": ["repeats", "accuses", "evenings", "refuses"]})


def test_exclusive_none_option_clears_others(definition: QuizDefinition) -> None:
    state = _state(definition, {"q5_changes": ["repeats", "none"]})
    assert state.answers["q5_changes"] == ["none"]
    assert "need:repeated_questions" not in state.tags


def test_unknown_option_id_rejected(definition: QuizDefinition) -> None:
    with pytest.raises(InvalidAnswer):
        _state(definition, {"q2_age": "ancient"})
    with pytest.raises(InvalidAnswer):
        _state(definition, {"q9_worries": ["what_to_say", "nope"]})


def test_scale_out_of_range_rejected(definition: QuizDefinition) -> None:
    for bad in (0, 6, "3", True, 2.5):
        with pytest.raises(InvalidAnswer):
            _state(definition, {"q11_confidence": bad})
    assert _state(definition, {"q11_confidence": 5}).answers["q11_confidence"] == 5


def test_non_skippable_empty_rejected(definition: QuizDefinition) -> None:
    for empty in (None, "", [], {}):
        with pytest.raises(InvalidAnswer):
            _state(definition, {"q2_age": empty})
    with pytest.raises(InvalidAnswer):
        _state(definition, {"q9_worries": []})


def test_skippable_empty_accepted(definition: QuizDefinition) -> None:
    state = _state(definition, {"q5_changes": []})
    assert state.answers["q5_changes"] == []
    assert state.last_question_id == "q5_changes"


def test_grid_missing_row_rejected(definition: QuizDefinition) -> None:
    with pytest.raises(InvalidAnswer):
        _state(definition, {"q10_documents": {"healthcare_proxy": "have"}})
    with pytest.raises(InvalidAnswer):  # unknown state
        _state(
            definition,
            {
                "q10_documents": {
                    "healthcare_proxy": "have",
                    "financial_poa": "have",
                    "hipaa_release": "maybe",
                }
            },
        )


def test_grid_all_have_derives_docs_ready(definition: QuizDefinition) -> None:
    rows = {"healthcare_proxy": "have", "financial_poa": "have", "hipaa_release": "have"}
    assert "docs:ready" in _state(definition, {"q10_documents": rows}).tags


def test_changing_q3_recalculates_branch_and_tags(definition: QuizDefinition) -> None:
    state = _state(definition, {"q1_recipient": "mom", "q3_situation": "recent"})
    assert state.branch == "recent"
    assert {"branch:recent", "stage:early", "new_diagnosis"} <= set(state.tags)
    state.answer(definition, "q3_situation", "hospital")
    assert state.branch == "changing"
    assert {"branch:changing", "after_hospital"} <= set(state.tags)
    assert not {"branch:recent", "stage:early", "new_diagnosis"} & set(state.tags)


def test_persona_c_tags_match_state_contract_example(definition: QuizDefinition) -> None:
    answers = {
        "q1_recipient": "mom",
        "q2_age": "75_84",
        "q3_situation": "recent",
        "q5_changes": ["repeats", "evenings"],
        "q6_living": "far",
        "q7_helpers": "just_me",
        "q8_work": "full_time",
        "q9_worries": ["what_to_say", "legal_money"],
        "q10_documents": {
            "healthcare_proxy": "have",
            "financial_poa": "missing",
            "hipaa_release": "not_sure",
        },
        "q11_confidence": 2,
        "q12_time": "10",
    }
    state = _state(definition, answers)
    assert state.tags == [
        "recipient:mom", "age:75_84", "age:65plus", "age:75plus", "branch:recent",
        "stage:early", "new_diagnosis", "need:repeated_questions", "need:evening_confusion",
        "living:far", "need:distance", "help:alone", "need:support_team", "work:full_time",
        "worry:communication", "worry:legal", "need:documents", "confidence:low", "pace:10",
    ]  # fmt: skip
    assert state.branch == "recent"
    assert state.last_question_id == "q12_time"


def test_confidence_tag_bands(definition: QuizDefinition) -> None:
    bands = {1: "low", 2: "low", 3: "mid", 4: "high", 5: "high"}
    for value, band in bands.items():
        tags = _state(definition, {"q11_confidence": value}).tags
        assert tags == [f"confidence:{band}"]


def test_locked_quiz_refuses_answers(definition: QuizDefinition) -> None:
    state = QuizState(uuid4(), locked=True)
    with pytest.raises(QuizLocked):
        state.answer(definition, "q1_recipient", "mom")


def test_interstitial_and_unknown_questions_are_not_answerable(definition: QuizDefinition) -> None:
    for question_id in ("reassure_1", "q99"):
        with pytest.raises(UnknownQuestion):
            _state(definition, {question_id: "x"})


def test_health_question_ids_flag_q3_and_q5(definition: QuizDefinition) -> None:
    assert definition.health_question_ids() == ("q3_situation", "q5_changes")
    assert derive(definition, {}).tags == ()


def test_unreadable_derived_condition_fails_loudly() -> None:
    with pytest.raises(QuizRuleError):
        parse_derived_rule("when the moon is full", "x")
