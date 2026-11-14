from datetime import date, timedelta

import pytest

from app.domain.schedule.entities import (
    LessonSchedule,
    PlanLessonRef,
    ScheduledLesson,
    UnlockRule,
)

RULE = UnlockRule(days_per_week=7, first_lesson_offset_days=0)  # content/plan-rules.json
START = date(2026, 1, 5)
IDS = ["l1", "l2", "l3", "l4", "l5"]


def offsets(per_week: int, n: int = 5) -> list[int]:
    rows = LessonSchedule.unlock_dates(START, per_week, IDS[:n], RULE)
    return [(r.unlock_on - START).days for r in rows]


def test_unlock_days_with_4_per_week_are_0_2_4_6_7() -> None:
    assert offsets(4) == [0, 2, 4, 6, 7]


@pytest.mark.parametrize(("per_week", "expected"), [(3, [0, 3, 5, 7, 10]), (5, [0, 2, 3, 5, 6])])
def test_3_per_week_and_5_per_week_formulas(per_week: int, expected: list[int]) -> None:
    assert offsets(per_week) == expected


def test_first_lesson_offset_is_added() -> None:
    rule = UnlockRule(7, 1)
    rows = LessonSchedule.unlock_dates(START, 4, IDS[:2], rule)
    assert [(r.unlock_on - START).days for r in rows] == [1, 3]


def plan(built: list[bool]) -> list[PlanLessonRef]:
    return [PlanLessonRef(f"l{i + 1}", b) for i, b in enumerate(built)]


def test_unbuilt_lessons_never_scheduled_and_marked_coming_later() -> None:
    lessons = plan([True, False, True, False])
    built = [x.lesson_id for x in lessons if x.built]
    rows = LessonSchedule.append_new([], built, 4, START, RULE)
    assert [r.lesson_id for r in rows] == ["l1", "l3"]
    assert [r.seq for r in rows] == [0, 1]  # k counts built lessons only
    assert [(r.unlock_on - START).days for r in rows] == [0, 2]
    states = LessonSchedule.statuses(lessons, rows, START + timedelta(days=30), set(), set())
    assert [s.status for s in states] == ["available", "coming_later", "available", "coming_later"]
    assert states[1].unlock_on is None


def test_new_built_lesson_appended_after_last_date_at_same_pace_and_existing_dates_unchanged() -> (
    None
):
    first = LessonSchedule.append_new([], ["l1", "l2", "l3"], 4, START, RULE)
    assert [(r.unlock_on - START).days for r in first] == [0, 2, 4]
    again = LessonSchedule.append_new(first, ["l1", "l2", "l3", "l4", "l5"], 4, START, RULE)
    assert [(r.lesson_id, r.seq, (r.unlock_on - START).days) for r in again] == [
        ("l4", 3, 6),
        ("l5", 4, 8),
    ]
    assert LessonSchedule.append_new(first, ["l1", "l2", "l3"], 4, START, RULE) == []
    # appended after the last date even when the start day moved
    moved = LessonSchedule.append_new(first, ["l1", "l2", "l3", "l4"], 4, date(2030, 1, 1), RULE)
    assert moved[0].unlock_on == START + timedelta(days=4 + 2)


def schedule_for(n: int) -> list[ScheduledLesson]:
    return LessonSchedule.unlock_dates(START, 4, IDS[:n], RULE)


def test_hero_is_first_unlocked_not_done_lesson() -> None:
    lessons = plan([True] * 5)
    sched = schedule_for(5)
    day2 = START + timedelta(days=2)  # l1, l2 unlocked
    states = LessonSchedule.statuses(lessons, sched, day2, {"l1"}, set())
    assert [s.status for s in states] == ["done", "available", "locked", "locked", "locked"]
    assert LessonSchedule.hero_lesson_id(states) == "l2"
    states = LessonSchedule.statuses(lessons, sched, day2, set(), {"l1"})
    assert states[0].status == "in_progress"
    assert LessonSchedule.hero_lesson_id(states) == "l1"
    states = LessonSchedule.statuses(lessons, sched, day2, {"l1", "l2"}, set())
    assert LessonSchedule.hero_lesson_id(states) is None


def test_unlocked_lessons_accumulate_regardless_of_completion() -> None:
    lessons = plan([True] * 5)
    sched = schedule_for(5)
    states = LessonSchedule.statuses(lessons, sched, START + timedelta(days=6), set(), set())
    assert [s.status for s in states] == ["available"] * 4 + ["locked"]
    assert states[4].unlock_on == START + timedelta(days=7)
    assert LessonSchedule.hero_lesson_id(states) == "l1"


def test_locked_lesson_in_progress_set_stays_locked() -> None:
    states = LessonSchedule.statuses(plan([True] * 2), schedule_for(2), START, set(), {"l2"})
    assert states[1].status == "locked"
