from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.checkins.use_cases import DoctorNoteInput, SubmitCheckin
from app.application.lessons.use_cases import GetLesson
from app.domain.lessons.plans import IfThenPlan, Task
from app.domain.lessons.progress import LessonProgress
from app.domain.session.entities import Session
from app.domain.today.checkins import (
    CheckinAlreadyAnswered,
    CheckinNotDue,
    CheckinPlanNotFound,
    InvalidCheckinAnswer,
)
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import with_plan
from tests.fakes.clock import FixedClock
from tests.fakes.sessions import FakeIdGenerator
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.lesson_content import make_content_dir


@pytest.fixture
def content(tmp_path: Path) -> JsonContentProvider:
    return JsonContentProvider.from_directory(make_content_dir(tmp_path / "content"))


def submit(uow: FakeUnitOfWork, content: JsonContentProvider, clock: FixedClock) -> SubmitCheckin:
    return SubmitCheckin(uow, content, FakeIdGenerator(), clock)


async def with_if_then_plan(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,
    variant: str = "in_person",
    response: str = "I point to the note.",
) -> Session:
    """A subscribed-style session with a lesson 1 plan and task made at the current app time."""
    session = await with_plan(uow, clock, content)
    now = session.app_now(clock.now())
    await uow.lesson_progress.save(LessonProgress(session.id, "m1_l1", now, variant=variant))
    await uow.if_then_plans.save(
        IfThenPlan(session.id, "m1_l1", "If Dad asks again,", response, "Take a breath", now)
    )
    await uow.tasks.save(Task(session.id, "m1_l1", "Write one note", "print", False, now))
    return session


async def test_checkin_not_due_on_same_app_day_and_due_next_day(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    with pytest.raises(CheckinNotDue):
        await submit(uow, content, clock).execute(session, "m1_l1", "not_yet", None)
    session.clock_offset = timedelta(days=1)  # "Simulate next day"
    result = await submit(uow, content, clock).execute(session, "m1_l1", "not_yet", None)
    assert result.response_text == "Your plan is ready for when it does."
    stored = await uow.checkins.get(session.id, "m1_l1")
    assert stored is not None and stored.came_up == "not_yet" and stored.outcome is None


async def test_checkin_quotes_users_own_plan_text(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content, response="I point to the note.")
    clock.advance(timedelta(days=1))
    result = await submit(uow, content, clock).execute(session, "m1_l1", "yes", "partly")
    assert result.plan.response == "I point to the note."
    assert result.plan.cue == "If Dad asks again," and result.plan.reset == "Take a breath"
    assert result.response_text is not None and result.response_text.startswith("That's normal")


async def test_didnt_help_returns_followups_from_lesson_file(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    result = await submit(uow, content, clock).execute(session, "m1_l1", "yes", "didnt_help")
    assert result.response_text == "That happens. Here are a few more ways to try."
    assert [f.title for f in result.follow_ups] == [
        "Look for a pattern",
        "Shorter, and written down",
        "Give him something to do",
    ]
    assert all("{" not in f.text for f in result.follow_ups)
    assert not result.task_done


async def test_helped_marks_task_done_and_counts_in_skills_source(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    result = await submit(uow, content, clock).execute(session, "m1_l1", "yes", "helped")
    assert result.task_done and result.follow_ups == []
    tasks = await uow.tasks.list_for_session(session.id)
    assert [t.done_at for t in tasks] == [session.app_now(clock.now())]
    helped = [c for c in await uow.checkins.list_for_session(session.id) if c.outcome == "helped"]
    assert len(helped) == 1  # what GetSkills (increment 29) counts


async def test_partly_leaves_the_task_open(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    await submit(uow, content, clock).execute(session, "m1_l1", "yes", "partly")
    assert (await uow.tasks.get(session.id, "m1_l1")) is not None
    task = await uow.tasks.get(session.id, "m1_l1")
    assert task is not None and task.done_at is None


async def test_doctor_note_creates_observation(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    result = await submit(uow, content, clock).execute(
        session, "m1_l1", "yes", "partly", DoctorNoteInput(True, "  Asked 6 times at dinner.  ")
    )
    assert result.observation_added
    [obs] = await uow.observations.list_for_session(session.id)
    assert obs.text == "Asked 6 times at dinner." and obs.add_to_visit_sheet
    assert obs.source == "doctor_note" and obs.lesson_id == "m1_l1"


async def test_doctor_note_without_text_uses_lesson_note_and_flag_off_is_kept(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    await submit(uow, content, clock).execute(
        session, "m1_l1", "yes", "partly", DoctorNoteInput(False)
    )
    [obs] = await uow.observations.list_for_session(session.id)
    assert obs.text.startswith("If repeated questions are new") and not obs.add_to_visit_sheet


async def test_no_doctor_note_no_observation(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    result = await submit(uow, content, clock).execute(session, "m1_l1", "yes", "helped")
    assert not result.observation_added
    assert await uow.observations.list_for_session(session.id) == []


async def test_noted_answer_of_not_yet_variant_adds_a_visit_sheet_observation(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content, variant="not_yet")
    clock.advance(timedelta(days=1))
    result = await submit(uow, content, clock).execute(session, "m1_l1", "noted", None)
    assert result.response_text == "Thank you. Your notes are on the doctor-visit sheet."
    [obs] = await uow.observations.list_for_session(session.id)
    assert obs.source == "checkin_noted" and obs.add_to_visit_sheet


async def test_checkin_for_unknown_or_other_session_plan_404(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    with pytest.raises(CheckinPlanNotFound):
        await submit(uow, content, clock).execute(session, "nope", "yes", "helped")
    other = Session(uuid4(), "h2", "UTC", timedelta(0), clock.now(), clock.now())
    with pytest.raises(CheckinPlanNotFound):
        await submit(uow, content, clock).execute(other, "m1_l1", "yes", "helped")


async def test_second_checkin_for_same_plan_409(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    await submit(uow, content, clock).execute(session, "m1_l1", "yes", "helped")
    with pytest.raises(CheckinAlreadyAnswered):
        await submit(uow, content, clock).execute(session, "m1_l1", "not_yet", None)


async def test_invalid_answers_are_rejected(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    clock.advance(timedelta(days=1))
    use_case = submit(uow, content, clock)
    with pytest.raises(InvalidCheckinAnswer):
        await use_case.execute(session, "m1_l1", "maybe", None)
    with pytest.raises(InvalidCheckinAnswer):
        await use_case.execute(session, "m1_l1", "yes", None)  # outcome is needed after "yes"
    with pytest.raises(InvalidCheckinAnswer):
        await use_case.execute(session, "m1_l1", "yes", "great")
    assert await uow.checkins.get(session.id, "m1_l1") is None


async def test_recap_includes_if_checkin_helped_text_only_when_previous_checkin_helped(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_if_then_plan(uow, clock, content)
    lesson = GetLesson(uow, content, clock)
    await lesson.execute(session, "m1_l1")  # schedules from day 0
    clock.advance(timedelta(days=10))
    before = await lesson.execute(session, "m1_l2")
    assert before.recap is not None and "You said it helped" not in before.recap.text
    await submit(uow, content, clock).execute(session, "m1_l1", "yes", "partly")
    partly = await lesson.execute(session, "m1_l2")
    assert partly.recap is not None and "You said it helped" not in partly.recap.text
    uow.checkins.rows.clear()
    await submit(uow, content, clock).execute(session, "m1_l1", "yes", "helped")
    helped = await lesson.execute(session, "m1_l2")
    assert helped.recap is not None
    assert helped.recap.text.endswith(
        "You said it helped. Today we'll make every conversation a little easier."
    )
