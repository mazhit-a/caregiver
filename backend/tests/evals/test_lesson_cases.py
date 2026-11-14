from collections import defaultdict
from pathlib import Path

from app.infrastructure.content.loader import load_content
from evals.case import EvalCase
from evals.dataset import GOLDEN_PATH, read_jsonl

REAL_CONTENT = Path(__file__).resolve().parents[3] / "content"
NEW_LESSONS = ("m1_l2", "m1_l3")


def _lesson_cases() -> dict[str, list[EvalCase]]:
    by_lesson: dict[str, list[EvalCase]] = defaultdict(list)
    for case in read_jsonl(GOLDEN_PATH):  # validates every line against the case schema
        if case.source == "lesson" and case.lesson_id:
            by_lesson[case.lesson_id].append(case)
    return by_lesson


def test_eval_cases_for_new_lessons_at_least_3_each_and_valid_against_dataset_schema() -> None:
    by_lesson = _lesson_cases()
    for lesson_id in NEW_LESSONS:
        cases = by_lesson[lesson_id]
        assert len(cases) >= 3, lesson_id
        assert all(c.check_note and c.check_note.startswith("needsContentReview") for c in cases)
        assert all(c.variant is None for c in cases)  # lessons without variants
        assert all(c.id.startswith(lesson_id.replace("m1_", "")) for c in cases)


def test_new_lesson_cases_cover_strong_weak_arguing_and_safety_kinds() -> None:
    for lesson_id in NEW_LESSONS:
        cases = _lesson_cases()[lesson_id]
        assert any(c.expect.score == 3 for c in cases), "strong"
        assert any(c.expect.argued is True for c in cases), "arguing"
        assert any(c.expect.argued is False and c.expect.score_max is not None for c in cases), (
            "weak"
        )
        flags = {f for c in cases for f in c.expect.flags}
        assert flags >= {"medical", "off_topic"}


def test_new_lesson_cases_use_the_lesson_round_lines() -> None:
    bundle = load_content(REAL_CONTENT)
    for lesson_id in NEW_LESSONS:
        lesson = bundle.lessons[lesson_id]
        screen = next(s for s in lesson.screens if s.type == "roleplay")
        rounds = screen.rounds_by_variant["default"]
        for case in _lesson_cases()[lesson_id]:
            assert case.rounds_total == len(rounds)
            line = rounds[case.round - 1].line
            assert case.parent_line == line, case.id
