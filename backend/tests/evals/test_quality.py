from pathlib import Path

import pytest

from evals.calibrate import JudgeNotCalibrated
from evals.client import CoachConfig
from evals.graders.judge import Judge, JudgeScores, JudgeUsage, load_judge_prompt
from evals.metrics import ConfigMetrics, compute_metrics, load_prices
from evals.quality import (
    UNJUDGED_COACH_UNAVAILABLE,
    UNJUDGED_JUDGE_FAILED,
    UNJUDGED_NO_MODEL_TEXT,
    aggregate_quality,
    judge_item_for,
    judge_measured,
    with_judged_quality,
)
from evals.runner import EvalContext
from evals.selection import SelectionError, select
from tests.evals.calibrate_helpers import passing_calibration
from tests.evals.conftest import make_case, make_measured, make_verdict
from tests.evals.judge_fakes import FakeJudgeClient, judge_response

MODEL = "claude-opus-5-5"


def _scores(b: int, t: int, p: int) -> JudgeScores:
    return JudgeScores(
        {"better_phrase": b, "tip": t, "parent_reaction": p},
        {"better_phrase": "r", "tip": "r", "parent_reaction": "r"},
        JudgeUsage(MODEL, 1, 1, 0, 0),
    )


def test_aggregation_is_mean_of_unit_scores_per_item_and_unjudged_are_counted() -> None:
    result = aggregate_quality(
        [_scores(5, 3, 1), _scores(3, 3, 1)],
        {UNJUDGED_COACH_UNAVAILABLE: 2, UNJUDGED_NO_MODEL_TEXT: 0},
        prompt_version="v1",
        model=MODEL,
        effort="medium",
    )
    assert result.per_item == {"better_phrase": 0.75, "tip": 0.5, "parent_reaction": 0.0}
    assert result.quality == pytest.approx(0.4166666)
    assert result.judged == 2 and result.unjudged == {UNJUDGED_COACH_UNAVAILABLE: 2}
    empty = aggregate_quality(
        [], {UNJUDGED_COACH_UNAVAILABLE: 3}, prompt_version="v1", model=MODEL, effort="medium"
    )
    assert empty.quality is None and empty.judged == 0


def test_only_coached_unflagged_outputs_are_judged(ctx: EvalContext) -> None:
    case = make_case()
    assert judge_item_for(make_measured(ctx, case)) is not None
    assert judge_item_for(make_measured(ctx, case, error="CoachUnavailable")) is None
    flagged = make_verdict(flags=("medical",))
    assert judge_item_for(make_measured(ctx, case, flagged)) is None


async def test_judging_blocked_before_any_call_without_calibration(
    ctx: EvalContext, tmp_path: Path
) -> None:
    client = FakeJudgeClient(judge_response(5, 5, 5))
    judge = Judge(client, prompt=load_judge_prompt(), model=MODEL)
    with pytest.raises(JudgeNotCalibrated):
        await judge_measured([make_measured(ctx, make_case())], judge, calibration_dir=tmp_path)
    assert client.requests == []


async def test_judge_measured_excludes_and_counts_unjudged(
    ctx: EvalContext, tmp_path: Path
) -> None:
    passing_calibration(tmp_path)
    ok1, ok2 = make_case(id="a"), make_case(id="b")
    measured = [
        make_measured(ctx, ok1),
        make_measured(ctx, ok2),
        make_measured(ctx, make_case(id="c"), error="CoachUnavailable"),
        make_measured(ctx, make_case(id="d"), make_verdict(flags=("medical",))),
        make_measured(ctx, make_case(id="e", parentLine="FAIL")),
    ]

    def answer(line: str):  # type: ignore[no-untyped-def]
        return None if line == "FAIL" else judge_response(5, 4, 3)

    judge = Judge(FakeJudgeClient(answer), prompt=load_judge_prompt(), model=MODEL)
    result = await judge_measured(measured, judge, concurrency=2, calibration_dir=tmp_path)
    assert result.judged == 2
    assert result.unjudged == {
        UNJUDGED_COACH_UNAVAILABLE: 1,
        UNJUDGED_NO_MODEL_TEXT: 1,
        UNJUDGED_JUDGE_FAILED: 1,
    }
    assert result.per_item == {"better_phrase": 1.0, "tip": 0.75, "parent_reaction": 0.5}
    assert result.calls == 3


# ------------------------------------------------------------------ selection integration


def _metrics(ctx: EvalContext, name: str) -> ConfigMetrics:
    case = make_case(id=f"c-{name}")
    measured = [make_measured(ctx, case, run=i) for i in range(2)]
    cfg = CoachConfig(name=name, model=MODEL, effort="low", prompt_version="1")
    return compute_metrics(cfg, measured, load_prices())


async def test_selection_uses_judged_quality_and_renormalises_when_absent(ctx: EvalContext) -> None:
    a, b = _metrics(ctx, "a"), _metrics(ctx, "b")
    none_absent = select([a, b])  # quality absent for ALL: weights renormalised
    assert none_absent.weights["quality"] == 0.0
    assert any("absent for ALL" in n for n in none_absent.notes)
    assert none_absent.weights["accuracy"] + none_absent.weights["consistency"] == pytest.approx(
        1.0
    )

    qa = aggregate_quality(
        [_scores(5, 5, 5)], {}, prompt_version="v1", model=MODEL, effort="medium"
    )
    qb = aggregate_quality(
        [_scores(1, 1, 1)], {}, prompt_version="v1", model=MODEL, effort="medium"
    )
    both = select([with_judged_quality(a, qa), with_judged_quality(b, qb)])
    assert both.weights["quality"] == pytest.approx(0.3)
    assert both.winner == "a"
    assert [r.quality for r in both.ranking] == [1.0, 0.0]

    with pytest.raises(SelectionError, match="only some"):
        select([with_judged_quality(a, qa), b])


def test_unjudgeable_configuration_leaves_quality_absent(ctx: EvalContext) -> None:
    empty = aggregate_quality(
        [], {UNJUDGED_COACH_UNAVAILABLE: 4}, prompt_version="v1", model=MODEL, effort="medium"
    )
    assert with_judged_quality(_metrics(ctx, "a"), empty).quality is None
