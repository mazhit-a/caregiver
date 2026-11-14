import json
from datetime import date
from pathlib import Path

import pytest

from app.infrastructure.config import Settings
from evals.calibrate import (
    AGREEMENT_THRESHOLD,
    CALIBRATION_DIR,
    JudgeNotCalibrated,
    RowResult,
    build_calibration_report,
    compute_agreement,
    judge_rows,
    main,
    require_calibration,
    write_calibration_report,
)
from evals.graders.judge import Judge, JudgePrompt, load_judge_prompt
from tests.evals.conftest import CONTENT_DIR
from tests.evals.judge_fakes import FakeJudgeClient, fixture_labels, label_row, scripted_scores

MODEL = "claude-opus-5-5"


def _rows(misses: dict[str, int], off_by_one: dict[str, int] | None = None) -> list[RowResult]:
    labels = fixture_labels()
    answers = scripted_scores(labels, misses, off_by_one)
    return [
        RowResult(
            lab.id,
            lab.human_scores(),
            answers[lab.parent_line].scores(),
        )
        for lab in labels
    ]


def test_calibration_agreement_computed_on_fixture_labels() -> None:
    # 2 + 3 + 1 pairs two away = 6 misses of 60; 2 of the remaining are one away (still agree).
    rows = _rows({"better_phrase": 2, "tip": 3, "parent_reaction": 1}, {"tip": 2})
    overall, per_item = compute_agreement(rows)
    assert overall.pairs == 60 and overall.within_one == 54
    assert overall.rate == pytest.approx(0.9)
    assert per_item["better_phrase"].rate == pytest.approx(0.9)
    assert per_item["tip"].rate == pytest.approx(0.85)
    assert per_item["parent_reaction"].rate == pytest.approx(0.95)
    # exact match is reported separately and is lower: 6 misses + 2 off-by-one pairs
    assert overall.exact == 52
    assert overall.exact_rate == pytest.approx(52 / 60)


def test_judge_failure_counts_as_disagreement() -> None:
    rows = [
        *_rows({})[:19],
        RowResult("x", {"better_phrase": 3, "tip": 3, "parent_reaction": 3}, None),
    ]
    overall, _ = compute_agreement(rows)
    assert overall.within_one == 57 and overall.pairs == 60


async def test_calibration_report_through_fake_client(tmp_path: Path) -> None:
    labels = fixture_labels()
    answers = scripted_scores(labels, {"better_phrase": 2, "tip": 3, "parent_reaction": 1})
    client = FakeJudgeClient(lambda line: answers[line])
    judge = Judge(client, prompt=load_judge_prompt(), model=MODEL)
    rows = await judge_rows(labels, judge, concurrency=4)
    report = build_calibration_report(
        rows,
        prompt=judge.prompt,
        model=MODEL,
        effort=judge.effort,
        labels_sha256="x",
        on=date(2026, 11, 14),
    )
    assert report["passed"] is True and report["labelCount"] == 20
    assert report["overall"]["agreement"] == pytest.approx(0.9)
    assert "within" not in json.dumps(report["rows"])  # ids and scores only, no output text
    assert "<= 1" in report["agreementDefinition"]
    path = write_calibration_report(report, tmp_path)
    assert require_calibration(judge.prompt, MODEL, judge.effort, tmp_path)["passed"] is True
    assert path.is_file()


def _report(
    tmp_path: Path, misses: dict[str, int], prompt: JudgePrompt | None = None
) -> JudgePrompt:
    prompt = prompt or load_judge_prompt()
    rows = _rows(misses)
    report = build_calibration_report(
        rows, prompt=prompt, model=MODEL, effort="medium", labels_sha256="x", on=date(2026, 11, 14)
    )
    write_calibration_report(report, tmp_path)
    return prompt


def test_judge_below_80_percent_is_blocked_from_selection(tmp_path: Path) -> None:
    # 12 of 60 pairs two away (4 per item) = 80% exactly passes; 13 misses = 78.3% overall blocks.
    prompt = _report(tmp_path, {"better_phrase": 4, "tip": 4, "parent_reaction": 4})
    assert require_calibration(prompt, MODEL, "medium", tmp_path)["passed"] is True
    prompt = _report(tmp_path, {"better_phrase": 5, "tip": 4, "parent_reaction": 4})
    with pytest.raises(JudgeNotCalibrated, match="below the 80%"):
        require_calibration(prompt, MODEL, "medium", tmp_path)


def test_per_item_agreement_below_threshold_blocks_even_if_overall_passes(tmp_path: Path) -> None:
    prompt = _report(tmp_path, {"better_phrase": 5, "tip": 0, "parent_reaction": 0})
    with pytest.raises(JudgeNotCalibrated, match="75%"):  # 15 of 20 on one item, overall 91.7%
        require_calibration(prompt, MODEL, "medium", tmp_path)


def test_gate_refuses_missing_stale_or_tampered_reports(tmp_path: Path) -> None:
    prompt = load_judge_prompt()
    with pytest.raises(JudgeNotCalibrated, match="no calibration report"):
        require_calibration(prompt, MODEL, "medium", tmp_path)
    _report(tmp_path, {})
    changed = JudgePrompt(prompt.version, prompt.system, "0" * 64)
    with pytest.raises(JudgeNotCalibrated, match="changed"):
        require_calibration(changed, MODEL, "medium", tmp_path)
    with pytest.raises(JudgeNotCalibrated, match="no calibration report"):
        require_calibration(prompt, "claude-sonnet-5-5", "medium", tmp_path)
    path = next(tmp_path.glob("*.json"))
    data = json.loads(path.read_text())
    data["overall"]["agreement"] = 0.5  # flag still says passed: numbers are re-checked
    path.write_text(json.dumps(data))
    with pytest.raises(JudgeNotCalibrated, match="below"):
        require_calibration(prompt, MODEL, "medium", tmp_path)
    path.write_text("{}")
    with pytest.raises(JudgeNotCalibrated, match="malformed"):
        require_calibration(prompt, MODEL, "medium", tmp_path)
    assert AGREEMENT_THRESHOLD == 0.8


def test_shipped_calibration_dir_has_no_report_yet() -> None:
    assert not list(CALIBRATION_DIR.glob("*.json")) if CALIBRATION_DIR.exists() else True


# ------------------------------------------------------------------ CLI


def _labels_file(tmp_path: Path) -> Path:
    path = tmp_path / "labels.jsonl"
    rows = [
        label_row(i, tuple(lab.human_scores().values()))  # type: ignore[arg-type]
        for i, lab in enumerate(fixture_labels())
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def _cli(tmp_path: Path, argv: list[str], client: FakeJudgeClient | None, **kw: object) -> int:
    return main(
        ["--labels", str(_labels_file(tmp_path)), "--report-dir", str(tmp_path / "rep"), *argv],
        settings=Settings(anthropic_api_key="", content_dir=CONTENT_DIR),
        client_factory=lambda _s: client,
        interactive=bool(kw.get("interactive", False)),
        today=date(2026, 11, 14),
    )


def test_cli_without_labels_file_fails_nonzero(tmp_path: Path) -> None:
    code = main(
        ["--labels", str(tmp_path / "nope.jsonl")],
        settings=Settings(anthropic_api_key="", content_dir=CONTENT_DIR),
        client_factory=lambda _s: None,
    )
    assert code == 1


def test_cli_dry_run_makes_no_call_and_refuses_without_confirmation(tmp_path: Path) -> None:
    client = FakeJudgeClient(None)
    assert _cli(tmp_path, ["--dry-run"], client) == 0
    assert _cli(tmp_path, [], client) == 3  # non-interactive without --yes: refused
    assert _cli(tmp_path, ["--yes", "--max-cost-usd", "0.0001"], client) == 3  # over the cap
    assert _cli(tmp_path, [], None) == 3  # no key
    assert client.requests == []


def test_cli_pass_and_fail_exit_codes(tmp_path: Path) -> None:
    labels = fixture_labels()
    good = scripted_scores(labels, {})
    bad = scripted_scores(labels, {"better_phrase": 20, "tip": 20, "parent_reaction": 20})
    ok = FakeJudgeClient(lambda line: good[line])
    assert _cli(tmp_path, ["--yes", "--max-cost-usd", "5"], ok) == 0
    assert len(ok.requests) == 20
    assert (
        _cli(tmp_path, ["--yes", "--max-cost-usd", "5"], FakeJudgeClient(lambda line: bad[line]))
        == 2
    )
