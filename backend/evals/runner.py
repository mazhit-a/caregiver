"""Runs eval cases through the PRODUCTION path: safety check -> `Coach.turn` -> `validate_verdict`
-> `apply_rules` (the same order as `SubmitRoleplayTurn`), then the code-based graders.

It takes a `Coach`, so it works with the real adapter, the adapter over a fake `ModelClient`, or a
scripted fake coach. It never calls a model on its own.
"""

import asyncio
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

from app.application.ports import Coach, CoachUnavailable
from app.domain.roleplay.errors import InvalidCoachOutput
from app.domain.roleplay.verdict import (
    CoachOutcome,
    CoachTips,
    CoachVerdict,
    apply_rules,
    validate_verdict,
)
from app.domain.safety.check import SafetyCheck, SafetyKind, SafetyTerms
from app.domain.shared.labels import RecipientLabels
from app.infrastructure.content.loader import load_content
from app.infrastructure.content.provider import JsonContentProvider
from app.infrastructure.llm.anthropic_coach import CallMetrics
from evals.cache import CacheEntry, ResultCache
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


def grade_attempt(
    case: EvalCase,
    ctx: EvalContext,
    run_index: int,
    verdict: CoachVerdict | None,
    error: str | None,
) -> CaseResult:
    """Domain rules and graders over one model verdict (or one failure). Pure and offline, so a
    cached verdict goes through exactly the same code as a live one."""
    local = SafetyCheck.classify(case.caregiver_reply, ctx.safety_terms)
    outcome: CoachOutcome | None = None
    if verdict is not None:
        try:
            outcome = apply_rules(
                validate_verdict(verdict), ctx.tips, ctx.labels_for(case.label), case.label
            )
        except InvalidCoachOutput as exc:
            error = type(exc).__name__
    return CaseResult(
        case_id=case.id,
        run_index=run_index,
        local_safety=local,
        outcome=outcome,
        error=error,
        grades=grade_case(case, outcome, local, ctx.grader_data),
    )


async def _ask(coach: Coach, case: EvalCase) -> tuple[CoachVerdict | None, str | None]:
    # A local crisis match never reaches the model in production. Here the model is still asked
    # (second layer, per the package notes) so its `crisis` flag can be checked as well.
    try:
        return await coach.turn(case.to_coach_input()), None
    except CoachUnavailable as exc:
        return None, type(exc).__name__


async def run_case(
    coach: Coach, case: EvalCase, ctx: EvalContext, run_index: int = 0
) -> CaseResult:
    verdict, error = await _ask(coach, case)
    return grade_attempt(case, ctx, run_index, verdict, error)


@dataclass(frozen=True)
class Measured:
    """One graded case run plus what the metrics need: the case, wall-clock time, the adapter's
    `CallMetrics` (usage; None for a fake coach or a cache entry without one)."""

    case: EvalCase
    result: CaseResult
    wall_ms: float
    call: CallMetrics | None
    cached: bool = False
    calls: tuple[CallMetrics, ...] = ()  # every model call of the case (parallel_split: 2)

    @property
    def usage_calls(self) -> tuple[CallMetrics, ...]:
        """The calls to price: all of them, or the single `call`."""
        if self.calls:
            return self.calls
        return () if self.call is None else (self.call,)


class CallRecorder:
    """Pass `recorder.sink` as `metrics_sink` to `build_eval_coach`. Each measured run captures
    its own call metrics through a context variable, so it is correct at any concurrency."""

    def __init__(self) -> None:
        self._slot: ContextVar[list[CallMetrics] | None] = ContextVar("eval_calls", default=None)

    def sink(self, metrics: CallMetrics) -> None:
        slot = self._slot.get()
        if slot is not None:
            slot.append(metrics)

    @contextmanager
    def capture(self) -> Iterator[list[CallMetrics]]:
        calls: list[CallMetrics] = []
        token = self._slot.set(calls)
        try:
            yield calls
        finally:
            self._slot.reset(token)


# Worst outcome wins when a case made several calls. `cancelled` is only ever the sibling of a
# call that failed, so the real failure ranks above it; an unknown outcome ranks above all known.
_OUTCOME_SEVERITY: Final = (
    "ok",
    "cancelled",
    "invalid_output",
    "max_tokens",
    "api_error",
    "refusal",
    "timeout",
    "no_api_key",
)
_ROLES: Final = ("single", "coach", "parent")


def _role_order(c: CallMetrics) -> int:
    return _ROLES.index(c.role) if c.role in _ROLES else len(_ROLES)


def _severity(outcome: str) -> int:
    return (
        _OUTCOME_SEVERITY.index(outcome) if outcome in _OUTCOME_SEVERITY else len(_OUTCOME_SEVERITY)
    )


def aggregate_calls(calls: Sequence[CallMetrics], wall_ms: float) -> CallMetrics | None:
    """One headline record per case. One call: itself, unchanged (single_call behaviour). Several
    (parallel_split: coach + parent): tokens and cache tokens SUMMED, latency = the measured case
    wall time (the calls ran concurrently: the max, never the sum), outcome = the worst of them.
    Model, effort, harness and prompt version come from the first call (coach role first); cost is
    priced per call from `Measured.calls`, not from this record."""
    if not calls:
        return None
    if len(calls) == 1:
        return calls[0]
    ordered = sorted(calls, key=_role_order)
    first = ordered[0]
    return replace(
        first,
        latency_ms=wall_ms,
        input_tokens=sum(c.input_tokens for c in ordered),
        output_tokens=sum(c.output_tokens for c in ordered),
        cache_read_tokens=sum(c.cache_read_tokens for c in ordered),
        cache_creation_tokens=sum(c.cache_creation_tokens for c in ordered),
        outcome=max((c.outcome for c in ordered), key=_severity),
        role="merged",
    )


async def _measure_one(
    coach: Coach,
    case: EvalCase,
    ctx: EvalContext,
    run_index: int,
    recorder: CallRecorder | None,
    cache: ResultCache | None,
    fingerprint: str | None,
) -> Measured:
    if cache is not None and fingerprint is not None:
        hit = cache.get(case, run_index, fingerprint)
        if hit is not None:
            result = grade_attempt(case, ctx, run_index, hit.verdict, None)
            return Measured(case, result, hit.wall_ms, hit.call, cached=True, calls=hit.calls)
    recorder = recorder or CallRecorder()
    with recorder.capture() as calls:
        started = time.perf_counter()
        verdict, error = await _ask(coach, case)
        wall_ms = round((time.perf_counter() - started) * 1000, 1)
    call = aggregate_calls(calls, wall_ms)
    kept = tuple(sorted(calls, key=_role_order)) if len(calls) > 1 else ()
    if verdict is not None and cache is not None and fingerprint is not None:
        cache.put(case, run_index, fingerprint, CacheEntry(verdict, wall_ms, call, kept))
    graded = grade_attempt(case, ctx, run_index, verdict, error)
    return Measured(case, graded, wall_ms, call, calls=kept)


async def run_measured(
    coach: Coach,
    cases: list[EvalCase],
    ctx: EvalContext,
    *,
    runs: int = 1,
    concurrency: int = 1,
    recorder: CallRecorder | None = None,
    cache: ResultCache | None = None,
    fingerprint: str | None = None,
) -> list[Measured]:
    """Run every case `runs` times and keep latency and usage. `concurrency=1` is the live
    sequential run; 4 is the production concurrency. Results are always in (run, case) order.
    A latency run must pass `cache=None` (cached wall times are history, not a live measurement).
    """
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    jobs = [(i, case) for i in range(runs) for case in cases]
    if concurrency == 1:
        return [await _measure_one(coach, c, ctx, i, recorder, cache, fingerprint) for i, c in jobs]
    gate = asyncio.Semaphore(concurrency)

    async def limited(i: int, c: EvalCase) -> Measured:
        async with gate:
            return await _measure_one(coach, c, ctx, i, recorder, cache, fingerprint)

    return list(await asyncio.gather(*(limited(i, c) for i, c in jobs)))


async def run_cases(
    coach: Coach, cases: list[EvalCase], ctx: EvalContext, runs: int = 1
) -> list[CaseResult]:
    """Sequential on purpose: a live run must not exceed the production concurrency of 4."""
    results: list[CaseResult] = []
    for run_index in range(runs):
        for case in cases:
            results.append(await run_case(coach, case, ctx, run_index))
    return results
