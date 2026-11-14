from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.today.use_cases import GetToday
from app.domain.care_card.entities import CardSnapshot, CareCard
from app.domain.lessons.progress import LessonProgress
from app.domain.phrases.entities import SavedPhrase
from app.domain.roleplay.run import RoleplayRun, RunContext, RunRecord
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import with_plan
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.lesson_content import make_content_dir

BANNED = ("fail", "miss", "behind", "late", "lost", "streak", "only", "should", "must", "guilt")


@pytest.fixture
def content(tmp_path: Path) -> JsonContentProvider:
    return JsonContentProvider.from_directory(make_content_dir(tmp_path / "content"))


def today(
    uow: FakeUnitOfWork, content: JsonContentProvider, clock: FixedClock, demo: bool = False
) -> GetToday:
    return GetToday(uow, content, clock, demo)


async def mark_done(uow: FakeUnitOfWork, session: Session, clock: FixedClock, lesson: str) -> None:
    await uow.lesson_progress.save(
        LessonProgress(session.id, lesson, clock.now(), done_at=clock.now())
    )


async def add_run(
    uow: FakeUnitOfWork, session: Session, context: RunContext, finished_at: datetime
) -> None:
    await uow.roleplay_runs.save(
        RunRecord(
            uuid4(),
            session.id,
            "m1_l1",
            context,
            None,
            finished_at - timedelta(minutes=5),
            RoleplayRun(rounds_total=2, turn_scores=[2]),
            finished_at=finished_at,
        )
    )


async def test_today_day_0_hero_is_lesson_1_and_no_checkin(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    view = await today(uow, content, clock).execute(session)
    assert view.check_in is None and view.practice_round is None
    assert view.next_step.kind == "lesson" and view.next_step.message is None
    assert view.next_step.lesson is not None
    assert view.next_step.lesson.lesson_id == "m1_l1" and view.next_step.lesson.reason
    assert view.title.startswith("Today with") and "{" not in view.title
    assert view.welcome_back is None and view.demo is None


async def test_today_rest_message_when_no_lesson_unlocked_not_done(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    await mark_done(uow, session, clock, "m1_l1")
    view = await today(uow, content, clock).execute(session)
    assert view.next_step.kind == "rest"
    assert view.next_step.message == "You're done for today. Rest counts too."
    assert view.next_step.lesson is not None and view.next_step.lesson.lesson_id == "m1_l2"
    assert view.next_step.lesson.status == "locked" and view.next_step.lesson.unlock_on is not None
    assert view.next_step.unlock_text is not None and "{" not in view.next_step.unlock_text


async def test_today_all_built_done_message(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    await mark_done(uow, session, clock, "m1_l1")
    await mark_done(uow, session, clock, "m1_l2")
    view = await today(uow, content, clock).execute(session)
    assert view.next_step.kind == "all_done" and view.next_step.lesson is None
    assert "New lessons are coming" in (view.next_step.message or "")


async def test_readiness_counts_first_30_days_modules_only(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    stored = uow.plans.rows[session.id]
    modules = stored.plan.modules
    first30_total = sum(len(m.lessons) for m in modules if m.in_first_30_days)
    assert 0 < first30_total < sum(len(m.lessons) for m in modules)
    await mark_done(uow, session, clock, "m1_l1")
    ring = (await today(uow, content, clock).execute(session)).readiness
    assert (ring.done, ring.total) == (1, first30_total)
    assert ring.text.endswith(f"1 of {first30_total} lessons done") and "{" not in ring.text
    # Module 1 outside the first 30 days: its lessons no longer count at all.
    outside = tuple(
        replace(m, in_first_30_days=False) if m.id == "m1_talking" else m for m in modules
    )
    uow.plans.rows[session.id] = replace(stored, plan=replace(stored.plan, modules=outside))
    ring = (await today(uow, content, clock).execute(session)).readiness
    assert ring.done == 0 and ring.total == first30_total - len(modules[0].lessons)


async def test_weekly_rhythm_counts_finished_runs_of_both_contexts_this_week_only(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)  # UTC; the clock is Monday 2026-01-05 09:00
    now = clock.now()
    await add_run(uow, session, RunContext.LESSON, now)
    await add_run(uow, session, RunContext.PRACTICE_ROUND, now + timedelta(days=2))
    await add_run(uow, session, RunContext.LESSON, now - timedelta(days=1))  # last Sunday
    unfinished = RoleplayRun(rounds_total=2)
    await uow.roleplay_runs.save(
        RunRecord(uuid4(), session.id, "m1_l1", RunContext.LESSON, None, now, unfinished)
    )
    clock.advance(timedelta(days=3))
    rhythm = (await today(uow, content, clock).execute(session)).weekly_rhythm
    stored = uow.plans.rows[session.id]
    assert (rhythm.done, rhythm.target) == (2, stored.lessons_per_week)
    assert rhythm.text == f"This week: 2 of {stored.lessons_per_week} practice sessions."


async def test_weekly_rhythm_copy_has_no_failure_framing(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    copy = content.today_copy()
    texts = [copy.weekly_rhythm, copy.readiness, copy.rest_message, copy.next_unlock]
    texts += [copy.welcome_back_title, copy.welcome_back_body, copy.all_built_done]
    view = await today(uow, content, clock).execute(session)
    texts += [view.weekly_rhythm.text, view.readiness.text]
    for text in texts:
        lowered = text.lower()
        assert not [w for w in BANNED if w in lowered], text
    zero = view.weekly_rhythm
    assert zero.done == 0 and "0 of" in zero.text  # an empty week is stated, not scolded


async def test_care_card_nudge_text_singular_and_plural(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    snapshot = CardSnapshot("Mom", (), (), (), "", (), (), (), clock.now().date(), None)
    await uow.care_cards.save(CareCard.publish("c" * 24, session.id, snapshot, [], clock.now()))
    later = clock.now() + timedelta(minutes=5)
    assert (await today(uow, content, clock).execute(session)).care_card_nudge is None
    texts = []
    for i in range(2):
        await uow.saved_phrases.add(
            SavedPhrase(uuid4(), session.id, f"p{i}", "scenario", None, later)
        )
        nudge = (await today(uow, content, clock).execute(session)).care_card_nudge
        assert nudge is not None and nudge.new_phrase_count == i + 1
        texts.append(nudge.text)
    assert texts == [
        "Your care card has 1 new phrase. Update it?",
        "Your care card has 2 new phrases. Update it?",
    ]
