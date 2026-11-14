"""Shared helpers: content context, case and verdict builders (no network, no key)."""

from pathlib import Path
from typing import Any

import pytest

from app.domain.roleplay.verdict import CoachOutcome, CoachVerdict, Goals, apply_rules
from evals.case import EvalCase, parse_case
from evals.runner import EvalContext, load_context

CONTENT_DIR = Path(__file__).resolve().parents[3] / "content"


@pytest.fixture(scope="session")
def ctx() -> EvalContext:
    return load_context(CONTENT_DIR)


def make_case(**overrides: Any) -> EvalCase:
    raw: dict[str, Any] = {
        "id": "t01",
        "source": "package",
        "round": 1,
        "parentLine": "When are we going to the doctor?",
        "parentMood": "worried",
        "caregiverReply": "You're wondering about tomorrow. I'll tell you when. Tea?",
        "expect": {"score": 3, "flags": []},
    }
    raw.update(overrides)
    return parse_case(raw)


def make_verdict(**overrides: Any) -> CoachVerdict:
    fields: dict[str, Any] = {
        "goals": Goals(True, True, True),
        "argued": False,
        "flags": (),
        "tip": "You named the worry and offered something to do.",
        "better_phrase": "Mom, you sound worried. I'm here. Want some tea?",
        "parent_reaction": "Tea sounds nice. Thank you.",
        "parent_mood": "calmer",
    }
    fields.update(overrides)
    return CoachVerdict(**fields)


def outcome_of(ctx: EvalContext, verdict: CoachVerdict, label: str = "Mom") -> CoachOutcome:
    return apply_rules(verdict, ctx.tips, ctx.labels_for(label), label)
