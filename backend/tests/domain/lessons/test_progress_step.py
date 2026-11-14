from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.lessons.errors import InvalidLessonStep
from app.domain.lessons.progress import LessonProgress

NOW = datetime(2026, 1, 5, tzinfo=UTC)


def _progress(done: bool = False) -> LessonProgress:
    return LessonProgress(uuid4(), "m1_l1", NOW, done_at=NOW if done else None)


def test_move_to_stores_a_valid_step() -> None:
    progress = _progress()
    progress.move_to(4, 9)
    assert progress.step == 4


@pytest.mark.parametrize("step", [-1, 9, 100])
def test_move_to_rejects_a_step_outside_the_screens(step: int) -> None:
    progress = _progress()
    with pytest.raises(InvalidLessonStep):
        progress.move_to(step, 9)
    assert progress.step == 0


def test_a_done_lesson_keeps_its_step() -> None:
    progress = _progress(done=True)
    progress.step = 7
    progress.move_to(1, 9)
    assert progress.step == 7
