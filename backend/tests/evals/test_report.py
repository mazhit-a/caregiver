"""Report writer: JSON + Markdown at evals/reports/<date>-<stage>.*"""

import json
from datetime import date
from pathlib import Path

import pytest

from evals.client import CoachConfig
from evals.metrics import compute_metrics, load_prices
from evals.report import ConfigRun, write_report
from evals.runner import EvalContext
from evals.selection import select
from tests.evals.conftest import make_call, make_case, make_measured

PRICES = load_prices()


def test_report_files_written_with_comparison_table(ctx: EvalContext, tmp_path: Path) -> None:
    case = make_case(expect={"score": 3})
    runs = []
    for name, model in (("opus-low", "claude-opus-5-5"), ("haiku-low", "claude-haiku-5-5")):
        config = CoachConfig(name=name, model=model, effort="low", prompt_version="1")
        measured = [
            make_measured(ctx, case, run=i, call=make_call(model=model), wall_ms=900.0 + i)
            for i in range(3)
        ]
        measured.append(make_measured(ctx, make_case(id="bad", expect={"score": 0}), run=0))
        metrics = compute_metrics(config, measured, PRICES)
        runs.append(ConfigRun(metrics, measured, {"model": model, "promptFileSha256": "abc"}))
    selection = select([r.metrics for r in runs])
    json_path, md_path = write_report(
        "model-effort",
        runs,
        selection,
        PRICES,
        dataset_split="dev",
        on=date(2026, 11, 14),
        out_dir=tmp_path,
    )
    assert json_path == tmp_path / "2026-11-14-model-effort.json"
    assert md_path == tmp_path / "2026-11-14-model-effort.md"
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    assert raw["selectionRule"]["weights"] == {"accuracy": 0.5, "quality": 0.3, "consistency": 0.2}
    assert raw["prices"]["retrievedOn"] == "2026-11-14"
    assert [c["name"] for c in raw["configs"]] == ["opus-low", "haiku-low"]
    assert raw["configs"][0]["cases"][0]["caseId"] == "t01"
    assert raw["configs"][0]["fingerprint"]["promptFileSha256"] == "abc"
    assert raw["selection"]["weights"]["quality"] == 0.0
    md = md_path.read_text(encoding="utf-8")
    assert "| config | safety recall |" in md
    assert "| opus-low |" in md and "| haiku-low |" in md
    assert "$/lesson" in md and "absent for ALL candidates" in md
    assert "## Failures" in md and "bad run 0" in md
    # No reply text is written anywhere.
    assert case.caregiver_reply not in md and case.caregiver_reply not in json_path.read_text()


def test_report_rejects_a_path_like_stage(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_report("../x", [], None, PRICES, dataset_split="dev", out_dir=tmp_path)
