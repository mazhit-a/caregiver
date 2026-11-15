import re
from datetime import UTC, datetime, timedelta

import pytest

from app.application.lessons.answer import AnswerLesson
from app.application.lessons.complete import CompleteLesson
from app.domain.lessons.errors import InvalidScreenAnswer, LessonLocked
from app.domain.lessons.plans import IF_THEN_RESPONSE_MAX
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import content, with_plan  # noqa: F401
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

APP_URL = "https://app.example.com"
ALL_FOUR = {"repeat": 3, "accusations": 2, "evenings": 4, "refusal": 1, "visits": 5}


def answerer(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> AnswerLesson:
    return AnswerLesson(uow, content, clock, public_app_url=APP_URL)


async def prepared(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
    timezone: str = "UTC",
) -> tuple[Session, AnswerLesson]:
    session = await with_plan(uow, clock, content)
    session.timezone = timezone
    use_case = answerer(uow, clock, content)
    await use_case.execute(session, "m1_l1", "setup", "phone")
    await use_case.execute(session, "m1_l1", "you", "r1")
    return session, use_case


async def test_plan_answer_saves_if_then_and_task_and_returns_reminder_for_next_evening_in_session_timezone(  # noqa: E501
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    # 2026-01-05 09:00 UTC is 01:00 in Los Angeles: the next evening is 19:00 the same local day.
    session, use_case = await prepared(uow, clock, content, "America/Los_Angeles")
    view = await use_case.execute(
        session,
        "m1_l1",
        "plan",
        {
            "response": "  You're wondering. I've got it. Want to help with tea?  ",
            "reminderDownloaded": True,
        },
    )
    result = view.result
    assert result["reminder"]["startsAt"] == "2026-01-05T19:00:00-08:00"
    assert result["reminder"]["timezone"] == "America/Los_Angeles"
    assert result["reminder"]["title"] == "Your plan for next time"
    assert result["reminder"]["url"] == f"{APP_URL}/lessons/m1_l1"
    description = result["reminder"]["description"]
    assert (
        "If Dad calls with the same question again, then I'll say: You're wondering." in description
    )
    assert "Save your phrase where you'll see it when Dad calls." in description
    assert "{" not in description

    plan = await uow.if_then_plans.get(session.id, "m1_l1")
    assert plan is not None
    assert plan.cue == "If Dad calls with the same question again,"
    assert plan.response.startswith("You're wondering") and plan.response.endswith("tea?")
    assert plan.reset == "take one slow breath"
    task = await uow.tasks.get(session.id, "m1_l1")
    assert task is not None and task.action == "copy_phrase" and task.reminder_downloaded
    assert result["ifThen"]["reset"] == "take one slow breath"


async def test_plan_answer_after_the_evening_rolls_to_the_next_day_and_replaces_the_plan(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    clock.set(datetime(2026, 1, 5, 20, 30, tzinfo=UTC))
    session, use_case = await prepared(uow, clock, content)
    first = await use_case.execute(session, "m1_l1", "plan", {"response": "One"})
    assert first.result["reminder"]["startsAt"] == "2026-01-06T19:00:00+00:00"
    await use_case.execute(session, "m1_l1", "plan", {"response": "Two"})
    plan = await uow.if_then_plans.get(session.id, "m1_l1")
    assert plan is not None and plan.response == "Two" and len(uow.if_then_plans.rows) == 1


async def test_reminder_date_uses_app_clock_offset(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await prepared(uow, clock, content)
    session.clock_offset = timedelta(days=3)
    view = await use_case.execute(session, "m1_l1", "plan", {"response": "Hi"})
    assert view.result["reminder"]["startsAt"] == "2026-01-08T19:00:00+00:00"


@pytest.mark.parametrize(
    "value, reason",
    [
        ({"response": "x" * (IF_THEN_RESPONSE_MAX + 1)}, "response_too_long"),
        ({"response": "   "}, "response_required"),
        ("just text", "value_must_be_an_object_with_response"),
        ({"response": "ok", "reminderDownloaded": "yes"}, "reminder_downloaded_must_be_boolean"),
    ],
)
async def test_plan_response_rejections(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
    value: object,
    reason: str,
) -> None:
    session, use_case = await prepared(uow, clock, content)
    with pytest.raises(InvalidScreenAnswer) as error:
        await use_case.execute(session, "m1_l1", "plan", value)
    assert error.value.details["reason"] == reason
    assert await uow.if_then_plans.get(session.id, "m1_l1") is None


async def test_plan_response_at_the_limit_is_accepted(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await prepared(uow, clock, content)
    await use_case.execute(session, "m1_l1", "plan", {"response": "x" * IF_THEN_RESPONSE_MAX})


async def test_wrap_first_lesson_sets_confidence_first_later_sets_latest(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await prepared(uow, clock, content)
    # The fixture lesson m1_l2 keeps `onlyFirstLesson: true`: no check there.
    first = await use_case.execute(session, "m1_l1", "wrap", ALL_FOUR)
    assert first.result == {"saved": True, "ratings": ALL_FOUR}
    ratings = await uow.confidence.get_ratings(session.id)
    assert ratings.first == ALL_FOUR and ratings.latest is None

    # Lesson 2 with the check made repeatable on every lesson.
    clock.advance(timedelta(days=10))
    later = AnswerLesson(uow, _repeatable_check(content, clock), clock, public_app_url=APP_URL)
    later_ratings = {**ALL_FOUR, "repeat": 5}
    await later.execute(session, "m1_l2", "wrap", later_ratings)
    ratings = await uow.confidence.get_ratings(session.id)
    assert ratings.first == ALL_FOUR and ratings.latest == later_ratings


def _repeatable_check(
    content: JsonContentProvider,  # noqa: F811
    clock: FixedClock,
) -> JsonContentProvider:
    class Repeatable:
        def __getattr__(self, name: str) -> object:
            return getattr(content, name)

        def render_lesson(self, *args: object, **kwargs: object) -> dict[str, object]:
            data = content.render_lesson(*args, **kwargs)  # type: ignore[arg-type]
            for screen in data["screens"]:  # type: ignore[attr-defined]
                if screen["type"] == "wrap":
                    screen["confidenceCheck"]["onlyFirstLesson"] = False
            return data

    return Repeatable()  # type: ignore[return-value]


@pytest.mark.parametrize(
    "ratings, reason",
    [
        ({**ALL_FOUR, "repeat": 6}, "rating_out_of_range"),
        ({**ALL_FOUR, "repeat": 0}, "rating_out_of_range"),
        ({**ALL_FOUR, "repeat": True}, "rating_must_be_an_integer"),
        ({**ALL_FOUR, "repeat": 2.5}, "rating_must_be_an_integer"),
        ({"repeat": 3}, "value_must_rate_every_item"),
        ({**ALL_FOUR, "bogus": 1}, "value_must_rate_every_item"),
        (3, "value_must_rate_every_item"),
    ],
)
async def test_slider_out_of_range_422(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
    ratings: object,
    reason: str,
) -> None:
    session, use_case = await prepared(uow, clock, content)
    with pytest.raises(InvalidScreenAnswer) as error:
        await use_case.execute(session, "m1_l1", "wrap", ratings)
    assert error.value.details["reason"] == reason
    assert (await uow.confidence.get_ratings(session.id)).first is None


async def test_wrap_check_only_on_first_lesson_is_refused_later(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await prepared(uow, clock, content)
    clock.advance(timedelta(days=10))
    with pytest.raises(InvalidScreenAnswer):
        await use_case.execute(session, "m1_l2", "wrap", ALL_FOUR)


async def test_complete_returns_next_lesson_with_reason_and_unlock_date(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, _ = await prepared(uow, clock, content)
    view = await CompleteLesson(uow, content, clock).execute(session, "m1_l1")
    assert view.done_at == clock.now()
    assert view.wrap is not None and view.wrap["skillLine"].startswith("New skill")
    assert "confidenceCheck" in view.wrap and re.search(r"\{\w+\}", str(view.wrap)) is None
    nxt = view.next_lesson
    assert nxt is not None and nxt.lesson_id == "m1_l2" and nxt.module_id == "m1_talking"
    schedule = await uow.lesson_schedule.list_for_session(session.id)
    assert nxt.unlock_on == next(s.unlock_on for s in schedule if s.lesson_id == "m1_l2")
    stored = await uow.plans.get(session.id)
    assert stored is not None
    reason = next(m.reason for m in stored.plan.modules if m.id == "m1_talking")
    assert nxt.reason == reason and reason
    assert view.all_done_line is None


async def test_complete_last_built_lesson_returns_all_done_message(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, _ = await prepared(uow, clock, content)
    clock.advance(timedelta(days=10))
    view = await CompleteLesson(uow, content, clock).execute(session, "m1_l2")
    assert view.next_lesson is None
    assert view.all_done_line is not None and "More are on the way" in view.all_done_line


async def test_complete_is_idempotent(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, _ = await prepared(uow, clock, content)
    complete = CompleteLesson(uow, content, clock)
    first = await complete.execute(session, "m1_l1")
    clock.advance(timedelta(hours=5))
    second = await complete.execute(session, "m1_l1")
    assert second.done_at == first.done_at == datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None and progress.done_at == first.done_at
    assert progress.screen_answers["you"] == "r1"


async def test_complete_locked_lesson_423(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await with_plan(uow, clock, content)
    with pytest.raises(LessonLocked):
        await CompleteLesson(uow, content, clock).execute(session, "m1_l2")
    assert await uow.lesson_progress.get(session.id, "m1_l2") is None
