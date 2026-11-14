from datetime import date
from pathlib import Path

from evals.calibrate import build_calibration_report, write_calibration_report
from evals.graders.judge import load_judge_prompt
from tests.evals.judge_fakes import fixture_labels, scripted_scores


def passing_calibration(directory: Path, model: str = "claude-opus-5-5") -> None:
    from evals.calibrate import RowResult

    labels = fixture_labels()
    answers = scripted_scores(labels, {})
    rows = [RowResult(x.id, x.human_scores(), answers[x.parent_line].scores()) for x in labels]
    report = build_calibration_report(
        rows,
        prompt=load_judge_prompt(),
        model=model,
        effort="medium",
        labels_sha256="x",
        on=date(2026, 11, 14),
    )
    write_calibration_report(report, directory)
