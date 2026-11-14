import json
from pathlib import Path

import pytest

from evals.labels import (
    HUMAN_LABELS_PATH,
    TEMPLATE_PATH,
    LabelError,
    load_labels,
    main,
    parse_labels,
    validate_labels,
)
from tests.evals.judge_fakes import HUMAN_PATTERN, fixture_labels, label_row


def _write(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def test_calibration_requires_at_least_20_labels(tmp_path: Path) -> None:
    ok = _write(tmp_path / "ok.jsonl", [label_row(i, (HUMAN_PATTERN[i],) * 3) for i in range(20)])
    assert len(load_labels(ok)) == 20
    short = _write(
        tmp_path / "short.jsonl", [label_row(i, (HUMAN_PATTERN[i],) * 3) for i in range(19)]
    )
    with pytest.raises(LabelError, match="at least 20"):
        load_labels(short)


def test_template_rows_are_not_labels() -> None:
    rows = parse_labels(TEMPLATE_PATH.read_text(encoding="utf-8"))
    assert len(rows) >= 1 and all(r.template for r in rows)
    with pytest.raises(LabelError, match="template"):
        validate_labels(rows, min_labels=1)


def test_no_fabricated_real_label_file_is_shipped() -> None:
    assert not HUMAN_LABELS_PATH.exists()


def test_label_validation_errors(tmp_path: Path) -> None:
    for bad in ({"human": {"betterPhrase": 6, "tip": 3, "parentReaction": 3}}, {"labeler": ""}):
        row = {**label_row(1, (3, 3, 3)), **bad}
        with pytest.raises(LabelError):
            parse_labels(json.dumps(row))
    dup = [label_row(1, (3, 3, 3)), label_row(1, (3, 3, 3))]
    with pytest.raises(LabelError, match="duplicate"):
        parse_labels("\n".join(json.dumps(r) for r in dup))
    with pytest.raises(LabelError, match="cannot read"):
        load_labels(tmp_path / "missing.jsonl")


def test_file_of_only_good_outputs_is_rejected() -> None:
    rows = parse_labels("\n".join(json.dumps(label_row(i, (5, 5, 5))) for i in range(20)))
    with pytest.raises(LabelError, match="lower"):
        validate_labels(rows)


def test_fixture_labels_are_valid() -> None:
    validate_labels(fixture_labels())


def test_validate_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(tmp_path / "none.jsonl")]) == 1
    assert main(["validate", str(TEMPLATE_PATH)]) == 1
    good = _write(tmp_path / "g.jsonl", [label_row(i, (HUMAN_PATTERN[i],) * 3) for i in range(20)])
    assert main(["validate", str(good)]) == 0
    assert "OK: 20 labels" in capsys.readouterr().out
