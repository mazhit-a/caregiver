import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.domain.plan.builder import PlanBuilder, PlanRulesError
from app.domain.plan.entities import (
    BoostRule,
    BuiltPlan,
    HeardFragment,
    PhraseRule,
    PlanRules,
)
from app.domain.shared.labels import RecipientLabels
from app.infrastructure.content.loader import load_content
from app.infrastructure.content.plan_rules_mapper import to_plan_rules

REPO = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture(scope="module")
def bundle_rules() -> tuple[PlanRules, dict[str, RecipientLabels]]:
    bundle = load_content(REPO / "content")
    labels = {
        k: RecipientLabels.from_mapping(m.model_dump(by_alias=True))
        for k, m in bundle.quiz.recipient_labels.items()
    }
    return to_plan_rules(bundle.plan_rules, bundle.phrases), labels


def _fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"persona_{name}.json").read_text())
    return data


def _build(
    fixture: dict[str, Any], rules: PlanRules, labels: dict[str, RecipientLabels]
) -> BuiltPlan:
    inp = fixture["input"]
    return PlanBuilder.build(
        tags=inp["tags"],
        branch=inp["branch"],
        labels=labels[inp["recipientKey"]],
        q5_order=inp["q5Order"],
        rules=rules,
        heard=[HeardFragment(h["slot"], h["text"]) for h in inp["heard"]],
    )


def _as_fixture_shape(plan: BuiltPlan) -> dict[str, Any]:
    return {
        "planIntro": plan.plan_intro,
        "whatWeHeard": list(plan.what_we_heard),
        "beforeAfter": {"before": plan.before_after.before, "after": plan.before_after.after},
        "modules": [
            {
                "id": m.id,
                "title": m.title,
                "reason": m.reason,
                "status": m.status,
                "inFirst30Days": m.in_first_30_days,
            }
            for m in plan.modules
        ],
        "first30Days": list(plan.first_30_days),
        "firstLessonId": plan.first_lesson_id,
        "quickGuides": [
            {"id": g.id, "title": g.title, "highlight": g.highlight} for g in plan.quick_guides
        ],
        "loaderLines": list(plan.loader_lines),
        "pace": {
            "lessonsPerWeek": plan.pace.lessons_per_week,
            "minutesPerLesson": plan.pace.minutes_per_lesson,
            "label": plan.pace.label,
        },
        "readiness": {
            "modulesTotal": plan.readiness.modules_total,
            "lessonsTotal": plan.readiness.lessons_total,
        },
        "giftPhraseIds": list(plan.gift_phrase_ids),
    }


def _titles(plan: BuiltPlan) -> list[str]:
    return [m.title for m in plan.modules]


def test_persona_a_noticing_dad(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    fixture = _fixture("a")
    plan = _build(fixture, rules, labels)
    assert _as_fixture_shape(plan) == fixture["expected"]
    assert _titles(plan)[:7] == [
        "Talking with Dad",
        "Before the diagnosis",
        "Hard moments",
        "While he can still decide",
        "Safe home, calmer days",
        "Doctors and your care team",
        "Caring for yourself",
    ]
    assert plan.pace.lessons_per_week == 3


def test_persona_b_recent_mom(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    fixture = _fixture("b")
    plan = _build(fixture, rules, labels)
    assert _as_fixture_shape(plan) == fixture["expected"]
    assert _titles(plan) == [
        "Talking with Mom",
        "While she can still decide",
        "Hard moments",
        "Doctors and your care team",
        "Caring for yourself",
        "Safe home, calmer days",
        "Getting more help",
        "Later stages",
    ]
    assert plan.what_we_heard == (
        "Mom was diagnosed in the last few months.",
        "Mom lives far away.",
        "You're handling most of it alone, and you work full-time.",
        "What worries you most: knowing what to say and legal papers and money.",
    )
    assert plan.plan_intro.startswith("This feels like a lot right now")


def test_persona_c_changing_hospital(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    fixture = _fixture("c")
    plan = _build(fixture, rules, labels)
    assert _as_fixture_shape(plan) == fixture["expected"]
    # "While she can still decide" and "Caring for yourself" tie at 75: list order wins.
    assert _titles(plan)[3:5] == ["While she can still decide", "Caring for yourself"]
    highlighted = [g.title for g in plan.quick_guides if g.highlight]
    assert highlighted == [
        "After a hospital stay",
        "If Mom goes missing",
        "After a fall",
        "You're at your limit",
    ]
    assert plan.quick_guides[0].title == "After a hospital stay"
    assert len(plan.what_we_heard) == 4 and "work" not in " ".join(plan.what_we_heard)


@pytest.mark.parametrize("name", ["a", "b", "c"])
def test_every_module_has_a_reason(
    name: str, bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]]
) -> None:
    rules, labels = bundle_rules
    plan = _build(_fixture(name), rules, labels)
    assert plan.modules and all(m.reason.strip() for m in plan.modules)
    assert not any("{" in m.reason or "{" in m.title for m in plan.modules)


def test_module_without_reason_is_rejected(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    broken = replace(
        rules,
        modules=tuple(
            replace(m, reason="") if m.id == "m7_more_help" else m for m in rules.modules
        ),
    )
    with pytest.raises(PlanRulesError):
        _build(_fixture("b"), broken, labels)


def test_noticing_branch_only_has_m0_before(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    ids_a = [m.id for m in _build(_fixture("a"), rules, labels).modules]
    ids_b = [m.id for m in _build(_fixture("b"), rules, labels).modules]
    ids_c = [m.id for m in _build(_fixture("c"), rules, labels).modules]
    assert ids_a[1] == "m0_before"
    assert "m0_before" not in ids_b and "m0_before" not in ids_c


def test_boost_none_logic_blocks_match(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    fixture = _fixture("a")
    tags = fixture["input"]["tags"]
    # worry:future boosts Hard moments by 10 unless branch:noticing (a `none` tag).
    noticing = PlanBuilder.build(tags, "noticing", labels["dad"], [], rules)
    hard = next(m for m in noticing.modules if m.id == "m2_hard_moments")
    assert hard.reason == "The same pattern, used when emotions run higher."
    boost = next(b for b in rules.boosts if b.points == 10 and b.none == ("branch:noticing",))
    recent_tags = [t for t in tags if t != "branch:noticing"] + ["branch:recent"]
    recent = PlanBuilder.build(recent_tags, "recent", labels["dad"], [], rules)
    hard_recent = next(m for m in recent.modules if m.id == "m2_hard_moments")
    assert hard_recent.reason == boost.reason


def test_highest_single_boost_sets_the_reason_and_ties_keep_first(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    synthetic = replace(
        rules,
        boosts=(
            BoostRule("m6_you", 10, "first ten", all=("x",)),
            BoostRule("m6_you", 10, "second ten", all=("x",)),
            BoostRule("m6_you", 5, "five", all=("x",)),
        ),
    )
    plan = PlanBuilder.build(["x"], "recent", labels["mom"], [], synthetic)
    assert next(m for m in plan.modules if m.id == "m6_you").reason == "first ten"


def test_gift_phrases_max_two_per_tag(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    phrases = (
        *(PhraseRule(f"t{i}", ("need:a",)) for i in range(4)),
        PhraseRule("g1", ("general",)),
        PhraseRule("g2", ("general",)),
        PhraseRule("g3", ("general",)),
    )
    plan = PlanBuilder.build(
        [], "recent", labels["mom"], ["need:a"], replace(rules, phrases=phrases)
    )
    assert plan.gift_phrase_ids == ("t0", "t1", "g1", "g2", "g3")


def test_gift_phrases_are_five_and_q5_order_first(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    plan = PlanBuilder.build(
        [],
        "recent",
        labels["mom"],
        ["need:wandering", "need:repeated_questions", "need:driving"],
        rules,
    )
    assert plan.gift_phrase_ids == ("p10", "p11", "p01", "p02", "p12")


def test_whatweheard_never_includes_q5(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    q5_fragment = HeardFragment("changes", "{Recipient} repeats questions.")
    plan = PlanBuilder.build(
        ["recipient:mom"],
        "recent",
        labels["mom"],
        ["need:repeated_questions"],
        rules,
        heard=[HeardFragment("situation", "{Recipient} {was} diagnosed."), q5_fragment],
    )
    assert plan.what_we_heard == ("Mom was diagnosed.",)
    assert not any("repeats" in s for s in plan.what_we_heard)


def test_whatweheard_skips_sentences_without_answers_and_ends_with_period(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    plan = PlanBuilder.build(
        [],
        "recent",
        labels["mom"],
        [],
        rules,
        heard=[HeardFragment("helpers", "A paid caregiver helps")],
    )
    assert plan.what_we_heard == ("A paid caregiver helps.",)


def test_loader_lines_at_most_four(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    everything = [t for b in rules.boosts for t in (*b.all, *(b.any or ()))]
    plan = PlanBuilder.build(everything, "recent", labels["mom"], [], rules)
    assert len(plan.loader_lines) == 4
    assert plan.loader_lines[0].startswith("Starting with how to talk")
    assert plan.loader_lines[-1].startswith("Setting the pace")


def test_pace_default_when_no_pace_tag(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    plan = PlanBuilder.build([], "recent", labels["mom"], [], rules)
    assert plan.pace.lessons_per_week == 4


def test_builder_is_pure(
    bundle_rules: tuple[PlanRules, dict[str, RecipientLabels]],
) -> None:
    rules, labels = bundle_rules
    fixture = _fixture("b")
    assert _build(fixture, rules, labels) == _build(fixture, rules, labels)
