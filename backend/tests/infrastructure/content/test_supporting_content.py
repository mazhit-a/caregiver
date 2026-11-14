import re
from pathlib import Path

from app.infrastructure.content.loader import load_content

REAL_CONTENT = Path(__file__).resolve().parents[4] / "content"
PROMPT = REAL_CONTENT / "prompts" / "roleplay-turn.md"


def _prompt_table_terms(kind: str) -> list[str]:
    rows = [line for line in PROMPT.read_text().splitlines() if line.startswith(f"| {kind} |")]
    assert len(rows) == 1
    return re.findall(r'"([^"]+)"', rows[0].split("|")[2])


def test_safety_terms_cover_every_prompt_file_example() -> None:
    terms = load_content(REAL_CONTENT).safety_terms
    crisis = _prompt_table_terms("Crisis")
    emergency = _prompt_table_terms("Emergency")
    assert len(crisis) == 9
    assert len(emergency) == 7
    assert set(crisis) <= set(terms.crisis)
    assert set(emergency) <= set(terms.emergency)
    assert terms.medical
    assert "missing the bus" in terms.matching.excluded_phrases


def test_crisis_resources_contains_911_988_helpline_aps() -> None:
    crisis = load_content(REAL_CONTENT).crisis_resources
    by_id = {r.id: r for r in crisis.resources}
    assert by_id["emergency_911"].phone == "911"
    assert by_id["lifeline_988"].phone == "988"
    assert "Alzheimer's Association 24/7 Helpline" in by_id["alz_helpline"].name
    assert "Adult Protective Services" in by_id["adult_protective_services"].name
    assert crisis.verify_before_launch is True


def test_visit_questions_have_ids_and_footer() -> None:
    visit = load_content(REAL_CONTENT).visit_questions
    ids = [q.id for q in visit.questions]
    assert ids and len(ids) == len(set(ids))
    assert all(q.text.strip() for q in visit.questions)
    assert visit.footer == "Family observations, not a medical assessment."


def test_pace_unlock_rule_loads() -> None:
    pace = load_content(REAL_CONTENT).plan_rules.pace
    rule = pace.unlock_rule
    assert rule.days_per_week == 7
    assert rule.first_lesson_offset_days == 0
    per_week = pace.lessons_per_week["default"]
    assert per_week == 4
    # TASK.md 6.7: with 4 lessons a week the unlock days are 0, 2, 4, 6, 7.
    days = [
        -(-k * rule.days_per_week // per_week) + rule.first_lesson_offset_days for k in range(5)
    ]
    assert days == [0, 2, 4, 6, 7]


def test_pricing_has_coupon_ids_for_every_plan() -> None:
    plans = load_content(REAL_CONTENT).pricing.plans
    assert plans
    for plan in plans:
        assert plan.stripe_intro_coupon_id
        assert plan.stripe_renew_price_id
