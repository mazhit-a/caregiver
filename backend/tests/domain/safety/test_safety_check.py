import json
from pathlib import Path

import pytest

from app.domain.safety.check import SafetyCheck, SafetyKind, SafetyTerms
from app.infrastructure.content.loader import load_content

CONTENT = Path(__file__).resolve().parents[4] / "content"


def real_terms() -> SafetyTerms:
    t = load_content(CONTENT).safety_terms
    return SafetyTerms(
        crisis=tuple(t.crisis),
        emergency=tuple(t.emergency),
        excluded_phrases=tuple(t.matching.excluded_phrases),
    )


def test_safety_matches_i_want_to_die_and_she_fell() -> None:
    terms = real_terms()
    assert SafetyCheck.classify("I can't do this, I want to die.", terms) is SafetyKind.CRISIS
    assert SafetyCheck.classify("She fell in the kitchen", terms) is SafetyKind.EMERGENCY
    assert (
        SafetyCheck.classify("I can\N{RIGHT SINGLE QUOTATION MARK}t find her anywhere", terms)
        is SafetyKind.EMERGENCY
    )


def test_safety_does_not_match_fellow_or_missing_the_bus() -> None:
    terms = real_terms()
    assert SafetyCheck.classify("My fellow caregiver helped", terms) is SafetyKind.NONE
    assert SafetyCheck.classify("I was missing the bus again", terms) is SafetyKind.NONE
    assert (
        SafetyCheck.classify("Missing the bus, and she is missing", terms) is SafetyKind.EMERGENCY
    )


def test_safety_is_case_insensitive_and_whole_word() -> None:
    terms = real_terms()
    assert SafetyCheck.classify("SUICIDE", terms) is SafetyKind.CRISIS
    assert SafetyCheck.classify("Want   To   Die", terms) is SafetyKind.CRISIS
    assert SafetyCheck.classify("suicidal thoughts", terms) is SafetyKind.NONE
    assert SafetyCheck.classify("hit her", terms) is SafetyKind.CRISIS
    assert SafetyCheck.classify("white her", terms) is SafetyKind.NONE
    assert SafetyCheck.classify("fell", terms) is SafetyKind.EMERGENCY
    assert SafetyCheck.classify("", terms) is SafetyKind.NONE


def test_crisis_wins_over_emergency() -> None:
    assert SafetyCheck.classify("she fell and I want to die", real_terms()) is SafetyKind.CRISIS


def test_every_localCheck_case_in_roleplay_evals_is_caught_by_safety_check() -> None:
    cases = json.loads((CONTENT / "evals" / "roleplay-evals.json").read_text())["cases"]
    assert len(cases) == 14
    flagged = [c for c in cases if c.get("localCheck")]
    assert flagged
    terms = real_terms()
    for case in flagged:
        assert SafetyCheck.classify(case["caregiverReply"], terms) is not SafetyKind.NONE, case[
            "id"
        ]


@pytest.mark.parametrize("term", ["kill myself", "end my life", "hurt him"])
def test_phrase_terms_match(term: str) -> None:
    assert SafetyCheck.classify(f"I might {term}.", real_terms()) is SafetyKind.CRISIS
