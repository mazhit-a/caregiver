import json
from pathlib import Path

import pytest

from evals.case import case_json_schema
from evals.dataset import (
    GOLDEN_PATH,
    PACKAGE_EVALS_PATH,
    DatasetError,
    Split,
    assert_disjoint,
    load_all_acknowledging_test,
    load_split,
    package_to_cases,
    read_jsonl,
    split_of,
)
from tests.evals.conftest import make_case


def test_golden_contains_the_14_package_cases_and_loads() -> None:
    cases = load_all_acknowledging_test(i_know_this_uses_the_test_set=True)
    package = [c for c in cases if c.source == "package"]
    original = json.loads(PACKAGE_EVALS_PATH.read_text(encoding="utf-8"))["cases"]
    assert len(package) == 14
    assert {c.id for c in package} == {c["id"] for c in original}
    # Defaults of the package are merged into every case, expectations are kept.
    e01 = next(c for c in package if c.id == "e01_all_three")
    assert (e01.label, e01.variant, e01.rounds_total, e01.calms) == (
        "Mom",
        "in_person",
        3,
        ("tea", "the garden"),
    )
    assert next(c for c in package if c.id == "e13_crisis_self").local_check is True


def test_golden_file_is_the_conversion_of_the_package_file() -> None:
    converted = package_to_cases(json.loads(PACKAGE_EVALS_PATH.read_text(encoding="utf-8")))
    on_disk = [c for c in read_jsonl(GOLDEN_PATH) if c.source == "package"]
    assert [c.to_json_line() for c in converted] == [c.to_json_line() for c in on_disk]


def test_split_is_deterministic_and_test_set_is_held_out() -> None:
    dev = load_split(Split.DEV)
    test = load_split(Split.TEST)
    assert dev and test
    assert {c.id for c in dev}.isdisjoint({c.id for c in test})
    assert len(dev) + len(test) == len(read_jsonl(GOLDEN_PATH))
    assert [c.id for c in load_split(Split.TEST)] == [c.id for c in test]
    assert all(split_of(c.id) is Split.TEST for c in test)
    assert_disjoint(dev, test)


def test_assignment_does_not_depend_on_other_cases() -> None:
    assert split_of("e10_medical_question") is split_of("e10_medical_question")
    assert split_of("anything-new") in (Split.DEV, Split.TEST)


def test_loaders_refuse_to_mix_splits_silently() -> None:
    with pytest.raises(DatasetError):
        load_all_acknowledging_test()
    with pytest.raises(DatasetError):
        load_split("all")  # type: ignore[arg-type]
    with pytest.raises(DatasetError):
        assert_disjoint([make_case(id="a")], [make_case(id="a")])


def test_duplicate_ids_and_invalid_lines_are_rejected(tmp_path: Path) -> None:
    line = make_case(id="dup").to_json_line()
    dup = tmp_path / "dup.jsonl"
    dup.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="duplicate"):
        read_jsonl(dup)
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "x", "unknown": 1}\n', encoding="utf-8")
    with pytest.raises(DatasetError, match=r"bad\.jsonl:1"):
        read_jsonl(bad)
    other = tmp_path / "other.jsonl"
    other.write_text(f"{line}\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="both"):
        load_split(Split.DEV, [dup.parent / "other.jsonl", other, other])


def test_case_schema_and_coach_input() -> None:
    schema = case_json_schema()
    assert "parentLine" in schema["properties"]
    case = make_case(calms=["tea"], previousTurns=[{"parent": "p", "caregiver": "c", "score": 2}])
    coach_input = case.to_coach_input()
    assert coach_input.caregiver_reply == case.caregiver_reply
    assert coach_input.calms == ("tea",)
    assert coach_input.previous_turns[0].score == 2
