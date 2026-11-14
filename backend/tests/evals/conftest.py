"""Shared helpers: content context, case and verdict builders (no network, no key)."""

from pathlib import Path
from typing import Any

import pytest

from app.domain.roleplay.verdict import CoachOutcome, CoachVerdict, Goals, apply_rules
from app.infrastructure.llm.anthropic_coach import CallMetrics
from evals.case import EvalCase, parse_case
from evals.runner import EvalContext, Measured, grade_attempt, load_context

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


def make_call(
    *,
    outcome: str = "ok",
    model: str = "claude-opus-5-5",
    input_tokens: int = 1000,
    output_tokens: int = 200,
    cache_read: int = 0,
    cache_write: int = 0,
    latency_ms: float = 1000.0,
) -> CallMetrics:
    return CallMetrics(
        harness="single_call",
        model=model,
        effort="low",
        prompt_version="1",
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_write,
        outcome=outcome,
    )


def make_measured(
    ctx: EvalContext,
    case: EvalCase,
    verdict: CoachVerdict | None = None,
    *,
    run: int = 0,
    wall_ms: float = 1000.0,
    call: CallMetrics | None = None,
    error: str | None = None,
) -> Measured:
    """A graded run through the production rules without any coach (offline)."""
    if verdict is None and error is None:
        verdict = make_verdict()
    if verdict is None:
        error = error or "CoachUnavailable"
    return Measured(case, grade_attempt(case, ctx, run, verdict, error), wall_ms, call)
