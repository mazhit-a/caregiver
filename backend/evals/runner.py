"""Runs eval cases through the PRODUCTION path: safety check -> `Coach.turn` -> `validate_verdict`
-> `apply_rules` (the same order as `SubmitRoleplayTurn`), then the code-based graders.

It takes a `Coach`, so it works with the real adapter, the adapter over a fake `ModelClient`, or a
scripted fake coach. It never calls a model on its own.
"""

from dataclasses import dataclass
from pathlib import Path

from app.application.ports import Coach, CoachUnavailable
from app.domain.roleplay.errors import InvalidCoachOutput
from app.domain.roleplay.verdict import CoachOutcome, CoachTips, apply_rules, validate_verdict
from app.domain.safety.check import SafetyCheck, SafetyKind, SafetyTerms
from app.domain.shared.labels import RecipientLabels
from app.infrastructure.content.loader import load_content
from app.infrastructure.content.provider import JsonContentProvider
from evals.case import EvalCase
from evals.graders.code import GraderData, GradeResult, grade_case, load_shaming_words


@dataclass(frozen=True)
class EvalContext:
    """Everything the production rules and the graders need, loaded from content."""

    safety_terms: SafetyTerms
    tips: CoachTips
    labels_by_recipient: dict[str, RecipientLabels]
    grader_data: GraderData

    def labels_for(self, label: str) -> RecipientLabels:
        """Labels whose recipient word equals the case label (default: the first entry)."""
        found = self.labels_by_recipient.get(label.lower())
        return found if found is not None else next(iter(self.labels_by_recipient.values()))


def load_context(content_dir: Path) -> EvalContext:
    bundle = load_content(content_dir)
    provider = JsonContentProvider(bundle)
    labels = {
        provider.recipient_labels(k).recipient.lower(): provider.recipient_labels(k)
        for k in provider.recipient_keys()
    }
    return EvalContext(
        safety_terms=provider.safety_terms(),
        tips=provider.coach_tips(),
        labels_by_recipient=labels,
        grader_data=GraderData(
            medical_terms=tuple(bundle.safety_terms.medical),
            shaming_words=load_shaming_words(),
        ),
    )


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    run_index: int
    local_safety: SafetyKind
    outcome: CoachOutcome | None  # None: the coach failed (CoachUnavailable / invalid output)
    error: str | None
    grades: tuple[GradeResult, ...]

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.grades)


async def run_case(
    coach: Coach, case: EvalCase, ctx: EvalContext, run_index: int = 0
) -> CaseResult:
    coach_input = case.to_coach_input()
    local = SafetyCheck.classify(case.caregiver_reply, ctx.safety_terms)
    outcome: CoachOutcome | None = None
    error: str | None = None
    # A local crisis match never reaches the model in production. Here the model is still asked
    # (second layer, per the package notes) so its `crisis` flag can be checked as well.
    try:
        verdict = validate_verdict(await coach.turn(coach_input))
        outcome = apply_rules(verdict, ctx.tips, ctx.labels_for(case.label), case.label)
    except (CoachUnavailable, InvalidCoachOutput) as exc:
        error = type(exc).__name__
    return CaseResult(
        case_id=case.id,
        run_index=run_index,
        local_safety=local,
        outcome=outcome,
        error=error,
        grades=grade_case(case, outcome, local, ctx.grader_data),
    )


async def run_cases(
    coach: Coach, cases: list[EvalCase], ctx: EvalContext, runs: int = 1
) -> list[CaseResult]:
    """Sequential on purpose: a live run must not exceed the production concurrency of 4."""
    results: list[CaseResult] = []
    for run_index in range(runs):
        for case in cases:
            results.append(await run_case(coach, case, ctx, run_index))
    return results
