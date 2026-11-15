"""Answer handlers of the new screen types and their wiring through the use cases (fakes only)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.application.lessons.answer import AnswerLesson
from app.application.lessons.handlers import SCREEN_HANDLERS, AnswerContext
from app.application.lessons.use_cases import GetLesson
from app.domain.lessons.errors import InvalidScreenAnswer, UnknownScreen
from app.domain.lessons.screens import RUNTIME_PLACEHOLDERS
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import with_plan
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.lesson_content_v2 import make_v2_content_dir

BLANKS = dict.fromkeys(RUNTIME_PLACEHOLDERS, "")
ROLEPLAY_TEXT = "TYPED-ROLEPLAY-SENTENCE"
_UUID = uuid4()
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def content(tmp_path: Path) -> JsonContentProvider:
    return JsonContentProvider.from_directory(make_v2_content_dir(tmp_path / "content"))


async def start(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider, variant: str = "phone"
) -> tuple[Session, AnswerLesson]:
    session = await with_plan(uow, clock, content)
    use_case = AnswerLesson(uow, content, clock)
    await use_case.execute(session, "m1_l1", "setup", variant)
    return session, use_case


def context(
    content: JsonContentProvider, screen_id: str, variant: str | None = "in_person"
) -> AnswerContext:
    data = content.render_lesson("m1_l1", "mom", variant, BLANKS)
    screen = next(s for s in data["screens"] if s["id"] == screen_id)
    return AnswerContext(
        session_id=_UUID, lesson_id="m1_l1", screen=screen, variant=variant,
        answered_at=_NOW, lesson=data,
    )  # fmt: skip


def run(content: JsonContentProvider, screen_id: str, value: object, **kw: Any) -> Any:
    ctx = context(content, screen_id, **kw)
    return SCREEN_HANDLERS[ctx.screen["type"]](ctx, value)


# ------------------------------------------------------------------ handlers (no I/O)


def test_setup_always_sets_the_variant(content: JsonContentProvider) -> None:
    outcome = run(content, "setup", "phone", variant=None)
    assert outcome.variant == "phone" and outcome.result == {"variant": "phone"}


def test_setup_rejects_an_option_that_is_not_on_the_screen(content: JsonContentProvider) -> None:
    with pytest.raises(InvalidScreenAnswer):
        run(content, "setup", "nope", variant=None)


def test_scenario_answer_uses_the_variant_options_and_save_flag_follows_the_verdict(
    content: JsonContentProvider,
) -> None:
    best = run(content, "scenario", "a1")
    assert best.result["verdict"] == "best" and best.result["savePhrase"] is True
    assert best.scenario_answer is not None and best.stored == {"scenario": "a1"}
    assert run(content, "scenario", "a2").result["savePhrase"] is False
    phone = run(content, "scenario", "a1", variant="phone")
    assert phone.result["verdict"] == "okay" and phone.result["savePhrase"] is False
    with pytest.raises(InvalidScreenAnswer):
        run(content, "scenario", "a2", variant="phone")  # only on the in_person screen


def test_quiz_reveals_the_correct_option_and_the_feedback_of_the_pick(
    content: JsonContentProvider,
) -> None:
    right = run(content, "check", "o2")
    assert right.result == {
        "optionId": "o2",
        "correct": True,
        "correctOptionId": "o2",
        "feedback": "That's right.",
    }
    wrong = run(content, "check", "o1")
    assert wrong.result["correct"] is False and wrong.result["correctOptionId"] == "o2"
    assert wrong.stored == {"check": "o1"}


@pytest.mark.parametrize("value", ["o9", 1, ["o1"], None])
def test_quiz_rejects_a_bad_value(content: JsonContentProvider, value: object) -> None:
    with pytest.raises(InvalidScreenAnswer):
        run(content, "check", value)


def test_builder_assembles_the_reply_server_side_and_flags_each_group(
    content: JsonContentProvider,
) -> None:
    ok = run(content, "build", ["o1", "o1"])
    assert ok.result == {
        "reply": "You seem worried. I am here.",
        "allCorrect": True,
        "groups": [{"correct": True}, {"correct": True}],
    }
    assert ok.stored == {"build": ["o1", "o1"]}
    mixed = run(content, "build", ["o2", "o1"])
    assert mixed.result["allCorrect"] is False
    assert mixed.result["groups"] == [{"correct": False}, {"correct": True}]


@pytest.mark.parametrize(
    "value", [["o1"], ["o1", "o1", "o1"], ["o1", "o9"], "o1", [1, 2], {"g1": "o1"}]
)
def test_builder_rejects_wrong_arity_unknown_options_and_wrong_types(
    content: JsonContentProvider, value: object
) -> None:
    with pytest.raises(InvalidScreenAnswer):
        run(content, "build", value)


def test_reset_returns_the_plan_wording_or_the_label(content: JsonContentProvider) -> None:
    assert run(content, "you", "r1").result == {"optionId": "r1", "text": "take one slow breath"}
    assert run(content, "you", "r2").result == {"optionId": "r2", "text": "Step away"}
    with pytest.raises(InvalidScreenAnswer):
        run(content, "you", "r3")


@pytest.mark.parametrize("screen_id", ["intro", "idea"])
def test_intro_and_content_take_no_answer(content: JsonContentProvider, screen_id: str) -> None:
    assert context(content, screen_id).screen["type"] not in SCREEN_HANDLERS


# ------------------------------------------------------------------ use cases


async def test_answers_persist_only_ids_and_scenario_rows(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session, use_case = await start(uow, clock, content, "in_person")
    await use_case.execute(session, "m1_l1", "scenario", "a1")
    await use_case.execute(session, "m1_l1", "check", "o1")
    await use_case.execute(session, "m1_l1", "build", ["o2", "o1"])
    await use_case.execute(session, "m1_l1", "you", "r2")
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None
    assert progress.screen_answers == {
        "setup": "in_person",
        "scenario": "a1",
        "check": "o1",
        "build": ["o2", "o1"],
        "you": "r2",
    }
    rows = await uow.scenario_answers.list_for_lesson(session.id, "m1_l1")
    assert [(r.screen_id, r.answer_id, r.verdict) for r in rows] == [("scenario", "a1", "best")]


async def test_typed_or_role_play_text_cannot_enter_the_stored_answers(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session, use_case = await start(uow, clock, content, "in_person")
    for screen_id, value in (("check", ROLEPLAY_TEXT), ("build", [ROLEPLAY_TEXT, ROLEPLAY_TEXT]),
                             ("you", ROLEPLAY_TEXT), ("scenario", ROLEPLAY_TEXT)):  # fmt: skip
        with pytest.raises(InvalidScreenAnswer):
            await use_case.execute(session, "m1_l1", screen_id, value)
    with pytest.raises(InvalidScreenAnswer):  # the role-play screen has no handler
        await use_case.execute(session, "m1_l1", "practice", ROLEPLAY_TEXT)
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None and ROLEPLAY_TEXT not in json.dumps(progress.screen_answers)
    assert await uow.scenario_answers.list_for_lesson(session.id, "m1_l1") == []


async def test_re_answering_a_quiz_keeps_the_last_pick(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session, use_case = await start(uow, clock, content)
    await use_case.execute(session, "m1_l1", "check", "o1")
    view = await use_case.execute(session, "m1_l1", "check", "o2")
    assert view.screen_type == "quiz" and view.result["correct"] is True
    progress = await uow.lesson_progress.get(session.id, "m1_l1")
    assert progress is not None and progress.screen_answers["check"] == "o2"


async def test_screens_after_the_setup_are_unknown_until_a_variant_is_chosen(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    with pytest.raises(UnknownScreen):
        await AnswerLesson(uow, content, clock).execute(session, "m1_l1", "check", "o1")


async def test_the_reset_pick_reaches_the_if_then_plan(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session, use_case = await start(uow, clock, content)
    await use_case.execute(session, "m1_l1", "you", "r1")
    view = await use_case.execute(session, "m1_l1", "plan", {"response": "say it slowly"})
    assert view.result["ifThen"]["reset"] == "take one slow breath"
    plan = await uow.if_then_plans.get(session.id, "m1_l1")
    assert plan is not None and plan.reset == "take one slow breath"


async def test_the_plan_has_no_reset_when_the_reset_screen_was_skipped(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session, use_case = await start(uow, clock, content)
    view = await use_case.execute(session, "m1_l1", "plan", {"response": "say it slowly"})
    assert view.result["ifThen"]["reset"] is None


async def test_the_lesson_view_counts_all_screens_even_before_the_variant_is_chosen(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    view = await GetLesson(uow, content, clock).execute(session, "m1_l1")
    assert len(view.lesson.screens) == 2 and view.screen_count == 10
    await AnswerLesson(uow, content, clock).execute(session, "m1_l1", "setup", "phone")
    view = await GetLesson(uow, content, clock).execute(session, "m1_l1")
    assert len(view.lesson.screens) == view.screen_count == 10
