import json
from pathlib import Path
from typing import Any

import pytest

from app.application.lessons.answer import AnswerLesson
from app.application.lessons.handlers import (
    SCREEN_HANDLERS,
    AnswerContext,
    AnswerOutcome,
    ScreenHandler,
)
from app.domain.lessons.errors import (
    InvalidScreenAnswer,
    LessonLocked,
    LessonNotAvailable,
    UnknownLesson,
    UnknownScreen,
)
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import content, with_plan  # noqa: F401
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

LESSON_FILE = Path(__file__).resolve().parents[4] / "content" / "lessons" / "m1_l1.json"


def answer_use_case(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
    handlers: dict[str, ScreenHandler] | None = None,
) -> AnswerLesson:
    return AnswerLesson(uow, content, clock, handlers)


async def set_up(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
    variant: str = "phone",
) -> tuple[Session, AnswerLesson]:
    session = await with_plan(uow, clock, content)
    use_case = answer_use_case(uow, clock, content)
    await use_case.execute(session, "m1_l1", "setup", variant)
    return session, use_case


def raw_screen(screen_id: str) -> dict[str, Any]:
    data = json.loads(LESSON_FILE.read_text())
    return next(s for s in data["screens"] if s["id"] == screen_id)


async def test_setup_answer_stores_variant_and_next_lesson_unchanged(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await with_plan(uow, clock, content)
    use_case = answer_use_case(uow, clock, content)
    # Read the lesson first so the schedule exists, then compare it after the answer.
    await use_case.execute(session, "m1_l1", "setup", "in_person")
    plan_before = await uow.plans.get(session.id)
    schedule_before = await uow.lesson_schedule.list_for_session(session.id)

    view = await use_case.execute(session, "m1_l1", "setup", "phone")

    assert view.screen_type == "setup" and view.result == {"variant": "phone"}
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None
    assert progress.variant == "phone" and progress.screen_answers["setup"] == "phone"
    assert await uow.plans.get(session.id) == plan_before
    assert await uow.lesson_schedule.list_for_session(session.id) == schedule_before


@pytest.mark.parametrize("variant", ["in_person", "phone", "both"])
async def test_scenario_returns_verdict_and_feedback_from_file_for_each_option(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
    variant: str,
) -> None:
    session, use_case = await set_up(uow, clock, content, variant)
    screen = raw_screen("scenario")
    file_variant = screen["optionsVariantMap"].get(variant, variant)
    for number, (_, verdict, _) in enumerate(screen["optionsByVariant"][file_variant], start=1):
        view = await use_case.execute(session, "m1_l1", "scenario", f"a{number}")
        assert view.result["verdict"] == verdict
        assert view.result["answerId"] == f"a{number}"
        assert view.result["feedback"]  # placeholders are filled
        assert "{" not in view.result["feedback"]
        assert view.result["savePhrase"] is (verdict == "best")


async def test_scenario_retry_with_other_answer_allowed_and_both_recorded(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await set_up(uow, clock, content)
    first = await use_case.execute(session, "m1_l1", "scenario", "a3")
    second = await use_case.execute(session, "m1_l1", "scenario", "a4")
    assert (first.result["verdict"], second.result["verdict"]) == ("try_again", "best")
    rows = await uow.scenario_answers.list_for_lesson(session.id, "m1_l1")
    assert [(r.answer_id, r.verdict) for r in rows] == [("a3", "try_again"), ("a4", "best")]
    assert rows[0].answered_at == clock.now()


async def test_reset_stores_the_pick_and_returns_the_plan_wording_quiz_returns_correctness(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await set_up(uow, clock, content)
    view = await use_case.execute(session, "m1_l1", "you", "r2")
    assert view.result == {"optionId": "r2", "text": "say the first words slowly"}
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None and progress.screen_answers["you"] == "r2"
    correct = await use_case.execute(session, "m1_l1", "q1", "o3")
    assert correct.result["correct"] is True and correct.result["feedback"]
    wrong = await use_case.execute(session, "m1_l1", "q1", "o1")
    assert wrong.result["correct"] is False and wrong.result["correctOptionId"] == "o3"


async def test_unknown_screen_id_422(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await set_up(uow, clock, content)
    with pytest.raises(UnknownScreen):
        await use_case.execute(session, "m1_l1", "nope", "a1")


async def test_screen_after_the_setup_screen_is_unknown_until_a_variant_is_chosen(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await with_plan(uow, clock, content)
    with pytest.raises(UnknownScreen):
        await answer_use_case(uow, clock, content).execute(session, "m1_l1", "scenario", "a1")


async def test_answer_option_not_in_screen_422(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await set_up(uow, clock, content)
    for screen_id, value in [
        ("setup", "carrier_pigeon"),
        ("scenario", "a9"),
        ("q1", "o9"),
        ("you", "r9"),
    ]:
        with pytest.raises(InvalidScreenAnswer) as error:
            await use_case.execute(session, "m1_l1", screen_id, value)
        assert error.value.details["reason"] == "option_not_on_screen"
    assert await uow.scenario_answers.list_for_lesson(session.id, "m1_l1") == []


@pytest.mark.parametrize("value", [3, None, ["a1"], {"id": "a1"}, True])
async def test_wrong_value_type_for_screen_type_422(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
    value: object,
) -> None:
    session, use_case = await set_up(uow, clock, content)
    for screen_id in ("setup", "scenario", "q1", "you"):
        with pytest.raises(InvalidScreenAnswer) as error:
            await use_case.execute(session, "m1_l1", screen_id, value)
        assert error.value.details["reason"] == "value_must_be_an_option_id"


async def test_screen_without_a_handler_or_mini_task_takes_no_answer(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session, use_case = await set_up(uow, clock, content)
    for screen_id in ("why1", "practice"):
        with pytest.raises(InvalidScreenAnswer) as error:
            await use_case.execute(session, "m1_l1", screen_id, "x")
        assert error.value.details["reason"] == "screen_takes_no_answer"


async def test_answer_to_locked_lesson_423(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await with_plan(uow, clock, content)
    use_case = answer_use_case(uow, clock, content)
    with pytest.raises(LessonLocked):
        await use_case.execute(session, "m1_l2", "scenario", "a1")
    assert await uow.lesson_progress.get(session.id, "m1_l2") is None
    assert uow.scenario_answers.rows == []


async def test_answer_to_unknown_and_unbuilt_lessons_404(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    session = await with_plan(uow, clock, content)
    use_case = answer_use_case(uow, clock, content)
    with pytest.raises(UnknownLesson):
        await use_case.execute(session, "nope", "s1", "a")
    with pytest.raises(LessonNotAvailable):
        await use_case.execute(session, "m1_l3", "s1", "a")


async def test_adding_a_new_screen_type_requires_only_registry_entry(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,  # noqa: F811
) -> None:
    def fake_roleplay(ctx: AnswerContext, value: object) -> AnswerOutcome:
        return AnswerOutcome({"echo": value}, {ctx.screen["id"]: "seen"})

    session, _ = await set_up(uow, clock, content)
    handlers = {**SCREEN_HANDLERS, "roleplay": fake_roleplay}
    use_case = answer_use_case(uow, clock, content, handlers)
    view = await use_case.execute(session, "m1_l1", "practice", "hello")
    assert view.screen_type == "roleplay" and view.result == {"echo": "hello"}
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None and progress.screen_answers["practice"] == "seen"
    # the default registry is untouched
    assert "roleplay" not in SCREEN_HANDLERS
