import pytest

from app.domain.roleplay.errors import InvalidReply
from app.domain.roleplay.run import (
    RoleplayRun,
    RunMode,
    TurnPhrases,
    best_phrase,
    validate_reply,
)
from app.domain.roleplay.verdict import (
    CoachTips,
    CoachVerdict,
    Goals,
    OutcomeKind,
    apply_rules,
)
from app.domain.shared.labels import RecipientLabels

LABELS = RecipientLabels.from_mapping(
    {
        "recipient": "Mom",
        "possessive": "Mom's",
        "pronoun": "she",
        "object": "her",
        "was": "was",
        "is": "is",
        "has": "has",
        "lives": "lives",
    }
)
TIPS = CoachTips(
    medical="For medical questions, ask {label}'s doctor or pharmacist. Keep going.",
    off_topic="Practice talking with {label}.",
    too_short="Try a full sentence.",
)


def verdict(
    n: bool = False,
    r: bool = False,
    o: bool = False,
    argued: bool = False,
    flags: tuple[str, ...] = (),
) -> CoachVerdict:
    return CoachVerdict(Goals(n, r, o), argued, flags, "model tip", "better", "react", "calmer")


def run_rules(v: CoachVerdict):  # type: ignore[no-untyped-def]
    return apply_rules(v, TIPS, LABELS, "Mom")


def test_score_equals_number_of_true_goals() -> None:
    assert run_rules(verdict()).score == 0
    assert run_rules(verdict(n=True)).score == 1
    assert run_rules(verdict(n=True, o=True)).score == 2
    assert run_rules(verdict(True, True, True)).score == 3


def test_argued_caps_score_at_2() -> None:
    assert run_rules(verdict(True, True, True, argued=True)).score == 2
    assert run_rules(verdict(True, argued=True)).score == 1


def test_model_claimed_score_is_ignored() -> None:
    # CoachVerdict has no score field: the model's number cannot reach the result.
    assert not hasattr(verdict(), "score")
    assert run_rules(verdict(r=True)).score == 1


def test_medical_flag_returns_fixed_tip_score_0_empty_reaction() -> None:
    out = run_rules(verdict(True, True, True, flags=("medical",)))
    assert out.score == 0
    assert out.parent_reaction == ""
    assert out.tip == "For medical questions, ask Mom's doctor or pharmacist. Keep going."
    assert out.goals.count == 0


def test_crisis_flag_returns_crisis_outcome() -> None:
    out = run_rules(verdict(True, flags=("medical", "crisis")))
    assert out.kind is OutcomeKind.CRISIS
    assert (out.score, out.tip, out.parent_reaction, out.better_phrase) == (0, "", "", "")


def test_off_topic_and_too_short_return_fixed_tips() -> None:
    off = run_rules(verdict(True, flags=("off_topic",)))
    assert (off.score, off.tip, off.parent_reaction) == (0, "Practice talking with Mom.", "react")
    short = run_rules(verdict(True, flags=("too_short",)))
    assert (short.score, short.tip) == (0, "Try a full sentence.")
    assert short.kind is OutcomeKind.COACHED


def _mode(run: RoleplayRun) -> RunMode:
    return run.mode


def test_run_once_in_fallback_stays_in_fallback() -> None:
    run = RoleplayRun(rounds_total=3)
    assert run.mode == RunMode.AI
    run.switch_to_fallback()
    run.record_turn(2, Goals(True, True, False))
    run.switch_to_fallback()
    assert _mode(run) == RunMode.FALLBACK
    assert not hasattr(run, "switch_to_ai")


def test_run_summary_first_vs_last() -> None:
    run = RoleplayRun(rounds_total=3)
    run.record_turn(1, Goals(True, False, False))
    run.record_turn(3, Goals(True, True, True))
    s = run.summary()
    assert (s.first_score, s.last_score, s.improved) == (1, 3, True)
    assert (s.notice_turns, s.reassure_turns, s.offer_turns) == (2, 1, 1)
    assert RoleplayRun(rounds_total=3).summary().first_score is None


def test_best_phrase_prefers_highest_scoring_reply_else_last_better_phrase() -> None:
    turns = [TurnPhrases(2, "a", "ba"), TurnPhrases(3, "b", "bb"), TurnPhrases(1, "c", "bc")]
    assert best_phrase(turns) == "b"
    assert best_phrase([TurnPhrases(2, "a", "ba"), TurnPhrases(1, "c", "bc")]) == "bc"
    assert best_phrase([]) is None


def test_reply_over_150_or_empty_rejected() -> None:
    assert validate_reply("  hi there ") == "hi there"
    assert len(validate_reply("a" * 150)) == 150
    for bad in ("", "   ", "a" * 151):
        with pytest.raises(InvalidReply):
            validate_reply(bad)
