"""Judged quality of one configuration: judge each coached output, aggregate, feed `with_quality`.

Rules:
- The judge must have a passing calibration (`require_calibration`), checked BEFORE any call.
- Only coached, unflagged outcomes carry model-written text worth judging. Everything else is
  UNJUDGED and counted by reason: `coach_unavailable` (no outcome), `no_model_text` (a flag
  replaced the tip / better phrase), `judge_failed` (the judge call failed).
- Per item: mean of (score-1)/4 over judged outputs. Quality = mean of the three item means
  (equal weights), normalised 0-1, or None when nothing could be judged.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from app.domain.roleplay.verdict import CoachOutcome, OutcomeKind
from evals.calibrate import CALIBRATION_DIR, require_calibration
from evals.graders.judge import (
    RUBRIC_ITEMS,
    Judge,
    JudgeItem,
    JudgeScores,
    JudgeUnavailable,
    to_unit,
)
from evals.metrics import ConfigMetrics
from evals.runner import Measured

UNJUDGED_COACH_UNAVAILABLE: Final = "coach_unavailable"
UNJUDGED_NO_MODEL_TEXT: Final = "no_model_text"
UNJUDGED_JUDGE_FAILED: Final = "judge_failed"


@dataclass(frozen=True)
class QualityResult:
    quality: float | None  # 0-1
    per_item: dict[str, float | None]  # 0-1 mean per rubric item
    judged: int
    unjudged: dict[str, int]
    judge_prompt_version: str
    judge_model: str
    judge_effort: str
    calls: int = 0
    reasons: dict[str, list[str]] = field(default_factory=dict)  # item -> reasons (no case text)


def judge_item_for(m: Measured) -> JudgeItem | None:
    """The exchange to judge, or None when the outcome has no model-written text to grade."""
    o: CoachOutcome | None = m.result.outcome
    if o is None or o.kind is not OutcomeKind.COACHED or o.flags:
        return None
    c = m.case
    return JudgeItem(
        label=c.label,
        parent_line=c.parent_line,
        parent_mood=c.parent_mood,
        caregiver_reply=c.caregiver_reply,
        tip=o.tip,
        better_phrase=o.better_phrase,
        parent_reaction=o.parent_reaction,
        coach_parent_mood=o.parent_mood,
        coach_score=o.score,
        previous_turns=tuple((t.parent, t.caregiver) for t in c.previous_turns),
    )


def aggregate_quality(
    scores: Sequence[JudgeScores],
    unjudged: dict[str, int],
    *,
    prompt_version: str,
    model: str,
    effort: str,
) -> QualityResult:
    """Pure aggregation: mean of unit scores per item, then mean of the item means."""
    per_item: dict[str, float | None] = {}
    for item in RUBRIC_ITEMS:
        values = [to_unit(s.scores[item]) for s in scores]
        per_item[item] = sum(values) / len(values) if values else None
    present = [v for v in per_item.values() if v is not None]
    return QualityResult(
        quality=sum(present) / len(present) if present else None,
        per_item=per_item,
        judged=len(scores),
        unjudged={k: v for k, v in unjudged.items() if v},
        judge_prompt_version=prompt_version,
        judge_model=model,
        judge_effort=effort,
        calls=len(scores) + unjudged.get(UNJUDGED_JUDGE_FAILED, 0),
        reasons={i: [s.reasons[i] for s in scores] for i in RUBRIC_ITEMS},
    )


async def judge_measured(
    measured: Sequence[Measured],
    judge: Judge,
    *,
    concurrency: int = 1,
    calibration_dir: Path = CALIBRATION_DIR,
) -> QualityResult:
    """Judge a configuration's runs. Raises `JudgeNotCalibrated` before any call if the judge has
    no passing calibration report."""
    require_calibration(judge.prompt, judge.model, judge.effort, calibration_dir)
    unjudged = {
        UNJUDGED_COACH_UNAVAILABLE: 0,
        UNJUDGED_NO_MODEL_TEXT: 0,
        UNJUDGED_JUDGE_FAILED: 0,
    }
    jobs: list[JudgeItem] = []
    for m in measured:
        item = judge_item_for(m)
        if item is not None:
            jobs.append(item)
        elif m.result.outcome is None:
            unjudged[UNJUDGED_COACH_UNAVAILABLE] += 1
        else:
            unjudged[UNJUDGED_NO_MODEL_TEXT] += 1
    gate = asyncio.Semaphore(concurrency)

    async def one(item: JudgeItem) -> JudgeScores | None:
        async with gate:
            try:
                return await judge.judge(item)
            except JudgeUnavailable:
                return None

    results = await asyncio.gather(*(one(j) for j in jobs))
    scored = [r for r in results if r is not None]
    unjudged[UNJUDGED_JUDGE_FAILED] = len(results) - len(scored)
    return aggregate_quality(
        scored,
        unjudged,
        prompt_version=judge.prompt.version,
        model=judge.model,
        effort=judge.effort,
    )


def with_judged_quality(metrics: ConfigMetrics, result: QualityResult) -> ConfigMetrics:
    """The metrics/selection path: `ConfigMetrics.with_quality` with the normalised 0-1 value."""
    return metrics.with_quality(result.quality)
