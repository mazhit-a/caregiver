import json
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.lessons.use_cases import GetLesson
from app.application.phrases.use_cases import SavePhrase
from app.application.plan.use_cases import CompleteQuiz
from app.application.quiz.use_cases import AnswerQuizQuestion
from app.domain.lessons.errors import LessonLocked, LessonNotAvailable, UnknownLesson
from app.domain.lessons.progress import LessonProgress
from app.domain.plan.errors import NoPlan
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.plan.test_plan_use_cases import PERSONA_A
from tests.fakes.clock import FixedClock
from tests.fakes.sessions import FakeIdGenerator
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.lesson_content import make_content_dir


@pytest.fixture
def content(tmp_path: Path) -> JsonContentProvider:
    return JsonContentProvider.from_directory(make_content_dir(tmp_path / "content"))


async def with_plan(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider, recipient: str = "dad"
) -> Session:
    session = Session(uuid4(), "h", "UTC", timedelta(0), clock.now(), clock.now())
    await uow.sessions.add(session)
    answer = AnswerQuizQuestion(uow, content)
    for question, value in {**PERSONA_A, "q1_recipient": recipient}.items():
        await answer.execute(session, question, value)
    await CompleteQuiz(uow, content, clock).execute(session)
    return session


def get_lesson(uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider) -> GetLesson:
    return GetLesson(uow, content, clock)


async def test_lesson_1_is_open_on_day_0_and_marked_started(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    view = await get_lesson(uow, clock, content).execute(session, "m1_l1")
    assert view.lesson.id == "m1_l1"
    assert view.progress.started_at == clock.now() and view.progress.step == 0
    stored = await uow.lesson_progress.get(session.id, "m1_l1")
    assert stored is not None and stored.started_at == clock.now()


async def test_started_at_is_kept_on_later_reads(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    first = await get_lesson(uow, clock, content).execute(session, "m1_l1")
    clock.advance(timedelta(hours=3))
    again = await get_lesson(uow, clock, content).execute(session, "m1_l1")
    assert again.progress.started_at == first.progress.started_at


async def test_locked_lesson_raises_with_unlock_on(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    with pytest.raises(LessonLocked) as error:
        await get_lesson(uow, clock, content).execute(session, "m1_l2")
    assert error.value.unlock_on > clock.now().date()
    assert error.value.details["unlockOn"] == error.value.unlock_on.isoformat()
    assert await uow.lesson_progress.get(session.id, "m1_l2") is None  # locked is not started


async def test_unknown_and_unbuilt_lessons(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    use_case = get_lesson(uow, clock, content)
    with pytest.raises(UnknownLesson):
        await use_case.execute(session, "nope")
    with pytest.raises(LessonNotAvailable):
        await use_case.execute(session, "m1_l3")


async def test_no_plan(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = Session(uuid4(), "h", "UTC", timedelta(0), clock.now(), clock.now())
    with pytest.raises(NoPlan):
        await get_lesson(uow, clock, content).execute(session, "m1_l1")


async def test_variant_applied_after_setup_answer(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    use_case = get_lesson(uow, clock, content)
    before = await use_case.execute(session, "m1_l1")
    assert before.lesson.variant is None and len(before.lesson.screens) == 2  # intro, setup
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None
    progress.variant = "phone"
    await uow.lesson_progress.save(progress)
    after = await use_case.execute(session, "m1_l1")
    assert after.lesson.variant == "phone" and len(after.lesson.screens) == 24
    scenario = next(s for s in after.lesson.screens if s["type"] == "scenario")
    assert "calls" in scenario["setup"]


async def test_a_stored_variant_the_lesson_no_longer_offers_is_ignored(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    await uow.lesson_progress.save(
        LessonProgress(session.id, "m1_l1", clock.now(), variant="removed")
    )
    view = await get_lesson(uow, clock, content).execute(session, "m1_l1")
    assert view.lesson.variant is None


async def test_lesson_without_variants_renders(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    await get_lesson(uow, clock, content).execute(session, "m1_l1")  # schedules from day 0
    clock.advance(timedelta(days=10))
    view = await get_lesson(uow, clock, content).execute(session, "m1_l2")
    assert view.lesson.variant is None
    assert view.lesson.screens[0]["type"] == "intro"
    assert len(view.lesson.screens) == 23  # the fixture is m1_l1 without its setup screen


@pytest.mark.parametrize("recipient", ["mom", "dad", "both", "in_law", "other"])
async def test_rendered_lesson_has_no_placeholder_for_mom_and_both(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider, recipient: str
) -> None:
    session = await with_plan(uow, clock, content, recipient)
    use_case = get_lesson(uow, clock, content)
    await use_case.execute(session, "m1_l1")
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None
    for variant in ("in_person", "phone", "both", "not_yet"):
        progress.variant = variant
        await uow.lesson_progress.save(progress)
        view = await use_case.execute(session, "m1_l1")
        text = json.dumps(view.lesson.screens) + view.lesson.title
        assert not re.search(r"\{\w+\}", text)


async def test_continue_where_you_left_off_returns_saved_step(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    await uow.lesson_progress.save(
        LessonProgress(session.id, "m1_l1", clock.now(), variant="phone", step=3)
    )
    view = await get_lesson(uow, clock, content).execute(session, "m1_l1")
    assert view.progress.step == 3 and view.lesson.variant == "phone"


async def test_lesson_2_recap_shows_previous_lesson_recap_with_saved_phrase(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    await SavePhrase(uow, FakeIdGenerator(), clock).execute(
        session, "I'm right here, Dad.", "roleplay", "m1_l1"
    )
    await get_lesson(uow, clock, content).execute(session, "m1_l1")  # schedules from day 0
    clock.advance(timedelta(days=10))
    view = await get_lesson(uow, clock, content).execute(session, "m1_l2")
    assert view.recap is not None and view.recap.from_lesson_id == "m1_l1"
    assert view.recap.text.startswith("Last time you practiced the three steps")
    assert 'Your phrase was: "I\'m right here, Dad."' in view.recap.text
    assert "{" not in view.recap.text


async def test_recap_without_saved_phrase_uses_content_fallback(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    # a phrase saved for another lesson (or from the gift sheet) is not this lesson's phrase
    await SavePhrase(uow, FakeIdGenerator(), clock).execute(session, "Gift one", "gift", None)
    await get_lesson(uow, clock, content).execute(session, "m1_l1")  # schedules from day 0
    clock.advance(timedelta(days=10))
    view = await get_lesson(uow, clock, content).execute(session, "m1_l2")
    assert view.recap is not None
    assert view.recap.text == (
        "Last time you practiced the three steps: notice the feeling, reassure, "
        "offer something to do."
    )


async def test_lesson_1_has_no_recap(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    view = await get_lesson(uow, clock, content).execute(session, "m1_l1")
    assert view.recap is None
