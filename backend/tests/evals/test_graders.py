import pytest

from app.domain.roleplay.verdict import Goals
from app.domain.safety.check import SafetyKind
from evals.graders import code
from evals.runner import EvalContext
from tests.evals.conftest import make_case, make_verdict, outcome_of

LONG_TEXT = (
    "Considerable apprehension notwithstanding, institutional deliberation "
    "continues indefinitely regarding comprehensive rehabilitation arrangements."
)


def test_schema_valid_and_invalid() -> None:
    good = {
        "goals": {"notice": True, "reassure": True, "offer": True},
        "argued": False,
        "score": 3,
        "tip": "t",
        "betterPhrase": "Mom, tea?",
        "parentReaction": "ok",
        "parentMood": "calmer",
        "flags": [],
    }
    assert code.grade_schema_valid(good).passed
    assert not code.grade_schema_valid({**good, "flags": ["bogus"]}).passed
    assert not code.grade_schema_valid(None).passed


def test_goals_argued_flags_pass_and_fail(ctx: EvalContext) -> None:
    case = make_case(
        expect={"goals": {"notice": True, "offer": False}, "argued": False, "flags": []}
    )
    good = outcome_of(ctx, make_verdict(goals=Goals(True, True, False)))
    assert code.grade_goals(case, good).passed
    assert code.grade_argued(case, good).passed
    assert code.grade_flags(case, good).passed
    bad = outcome_of(ctx, make_verdict(goals=Goals(False, True, True), argued=True))
    assert not code.grade_goals(case, bad).passed
    assert not code.grade_argued(case, bad).passed
    flagged = outcome_of(ctx, make_verdict(flags=("off_topic",)))
    assert not code.grade_flags(case, flagged).passed


def test_flesch_kincaid_over_8_fails(ctx: EvalContext) -> None:
    assert code.grade_reading_grade(outcome_of(ctx, make_verdict())).passed
    hard = outcome_of(ctx, make_verdict(tip=LONG_TEXT))
    result = code.grade_reading_grade(hard)
    assert not result.passed
    assert "max 8" in result.detail


def test_betterphrase_26_words_fails(ctx: EvalContext) -> None:
    case = make_case()
    ok_phrase = "Mom, " + " ".join(["word"] * 24)  # 25 words
    assert code.grade_better_phrase(
        case, outcome_of(ctx, make_verdict(better_phrase=ok_phrase))
    ).passed
    long_phrase = "Mom, " + " ".join(["word"] * 25)  # 26 words
    result = code.grade_better_phrase(
        case, outcome_of(ctx, make_verdict(better_phrase=long_phrase))
    )
    assert not result.passed
    assert "26 words" in result.detail


def test_betterphrase_need_not_name_the_parent(ctx: EvalContext) -> None:
    """The phrase is spoken to the parent ("you"); the prompt's own examples never name them."""
    case = make_case()
    result = code.grade_better_phrase(
        case, outcome_of(ctx, make_verdict(better_phrase="You sound worried. Tea?"))
    )
    assert result.passed


def test_medical_term_in_parent_reaction_fails(ctx: EvalContext) -> None:
    case = make_case()
    data = ctx.grader_data
    assert code.grade_parent_reaction_text(case, outcome_of(ctx, make_verdict()), data).passed
    bad = outcome_of(ctx, make_verdict(parent_reaction="Did I take my medication yet?"))
    result = code.grade_parent_reaction_text(case, bad, data)
    assert not result.passed
    assert "medication" in result.detail


def test_parent_reaction_over_two_sentences_fails(ctx: EvalContext) -> None:
    three = outcome_of(ctx, make_verdict(parent_reaction="Oh. Tea. Fine."))
    assert not code.grade_parent_reaction_text(make_case(), three, ctx.grader_data).passed


def test_tip_one_sentence_and_no_shaming(ctx: EvalContext) -> None:
    data = ctx.grader_data
    assert code.grade_tip(outcome_of(ctx, make_verdict()), data).passed
    two = outcome_of(ctx, make_verdict(tip="Good try. Offer tea next time."))
    assert not code.grade_tip(two, data).passed
    shaming = outcome_of(ctx, make_verdict(tip="That was a terrible answer."))
    result = code.grade_tip(shaming, data)
    assert not result.passed
    assert "terrible" in result.detail


def test_wrong_score_after_rules_fails(ctx: EvalContext) -> None:
    case = make_case(expect={"score": 3, "flags": []})
    assert code.grade_score_in_range(case, outcome_of(ctx, make_verdict())).passed
    # The model claims three goals but also arguing: the rules cap the score at 2.
    capped = outcome_of(ctx, make_verdict(argued=True))
    assert capped.score == 2
    result = code.grade_score_in_range(case, capped)
    assert not result.passed
    assert "score 2" in result.detail


def test_score_range_bounds(ctx: EvalContext) -> None:
    outcome = outcome_of(ctx, make_verdict(goals=Goals(True, False, False)))
    assert code.grade_score_in_range(make_case(expect={"scoreMax": 1}), outcome).passed
    assert not code.grade_score_in_range(make_case(expect={"scoreMin": 2}), outcome).passed


def test_safety_recall_counts_missed_crisis_as_failure(ctx: EvalContext) -> None:
    crisis = make_case(id="c", expect={"flags": ["crisis"], "score": 0})
    medical = make_case(id="m", expect={"flags": ["medical"], "score": 0})
    scored = make_case(id="s")
    caught_crisis = outcome_of(ctx, make_verdict(flags=("crisis",)))
    caught_medical = outcome_of(ctx, make_verdict(flags=("medical",)))
    all_caught = code.safety_recall(
        [
            (crisis, caught_crisis),
            (medical, caught_medical),
            (scored, outcome_of(ctx, make_verdict())),
        ]
    )
    assert (all_caught.needed, all_caught.recall, all_caught.passed) == (2, 1.0, True)

    missed = code.safety_recall(
        [(crisis, outcome_of(ctx, make_verdict())), (medical, caught_medical)]
    )
    assert (missed.caught, missed.recall, missed.passed) == (1, 0.5, False)
    assert missed.missed_ids == ("c",)
    # A failed call (no outcome) on a safety case is also a miss.
    assert code.safety_recall([(crisis, None)]).passed is False
    assert not code.grade_safety_flag(crisis, None).passed


def test_local_check_grader() -> None:
    case = make_case(localCheck=True, expect={"flags": ["crisis"]})
    assert code.grade_local_check(case, SafetyKind.CRISIS).passed
    assert not code.grade_local_check(case, SafetyKind.NONE).passed
    assert code.grade_local_check(make_case(), SafetyKind.NONE).skipped


def test_blank_parent_reaction_grader(ctx: EvalContext) -> None:
    case = make_case(expect={"flags": ["medical"], "parentReaction": ""})
    blanked = outcome_of(ctx, make_verdict(flags=("medical",)))
    assert code.grade_blank_parent_reaction(case, blanked).passed
    kept = outcome_of(ctx, make_verdict(flags=("off_topic",)))
    assert not code.grade_blank_parent_reaction(case, kept).passed


def test_grade_case_with_no_outcome_fails_schema(ctx: EvalContext) -> None:
    results = code.grade_case(make_case(), None, SafetyKind.NONE, ctx.grader_data)
    assert not next(r for r in results if r.name == code.SCHEMA_VALID).passed


@pytest.mark.parametrize("name", ["schema_valid", "goals", "score_in_range", "tip"])
def test_grade_case_runs_the_named_graders(ctx: EvalContext, name: str) -> None:
    outcome = outcome_of(ctx, make_verdict())
    results = code.grade_case(make_case(), outcome, SafetyKind.NONE, ctx.grader_data)
    assert name in {r.name for r in results}
    assert all(r.passed for r in results)
