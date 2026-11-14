from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.skills.use_cases import GetSkills
from app.domain.lessons.plans import Task
from app.domain.lessons.progress import ScenarioAnswer
from app.domain.phrases.entities import SavedPhrase
from app.domain.roleplay.run import RoleplayRun, RunContext, RunRecord
from app.domain.roleplay.verdict import Goals
from app.domain.session.entities import Session
from app.domain.today.checkins import Checkin
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.lessons.test_get_lesson import with_plan
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.lesson_content import make_content_dir


@pytest.fixture
def content(tmp_path: Path) -> JsonContentProvider:
    return JsonContentProvider.from_directory(make_content_dir(tmp_path / "content"))


def use_case(uow: FakeUnitOfWork, content: JsonContentProvider, clock: FixedClock) -> GetSkills:
    return GetSkills(uow, content, clock)


async def add_run(
    uow: FakeUnitOfWork, session: Session, clock: FixedClock, scores: list[int], hours: int
) -> None:
    run = RoleplayRun(rounds_total=len(scores), turn_scores=scores)
    run.goals_hit = [Goals(True, False, False)] * len(scores)
    start = clock.now() + timedelta(hours=hours)
    await uow.roleplay_runs.save(
        RunRecord(
            uuid4(),
            session.id,
            "m1_l1",
            RunContext.LESSON,
            "phone",
            start,
            run,
            finished_at=start + timedelta(minutes=5),
        )
    )


async def test_skills_first_vs_latest_roleplay_score_after_two_runs(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    await add_run(uow, session, clock, [1, 2, 2], hours=1)
    await add_run(uow, session, clock, [2, 3, 3], hours=5)
    unfinished = RoleplayRun(rounds_total=3, turn_scores=[0])
    await uow.roleplay_runs.save(
        RunRecord(uuid4(), session.id, "m1_l1", RunContext.LESSON, None, clock.now(), unfinished)
    )
    view = await use_case(uow, content, clock).execute(session)
    assert [s.id for s in view.skills] == ["communication"]
    skill = view.skills[0]
    assert skill.label == "Communication"
    assert skill.roleplay is not None
    assert (skill.roleplay.runs, skill.roleplay.first_score, skill.roleplay.latest_score) == (
        2,
        1,
        3,
    )
    assert skill.roleplay.max_score == 3 and skill.scenarios is None


async def test_skills_counts_scenarios_phrases_tasks_and_helped_tasks(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    now = clock.now()
    for screen, verdict in [("s2", "okay"), ("s2", "best"), ("s3", "try_again")]:
        await uow.scenario_answers.add(
            ScenarioAnswer(session.id, "m1_l1", screen, "a", verdict, now)
        )
    for text in ("one", "two"):
        await uow.saved_phrases.add(
            SavedPhrase.create(uuid4(), session.id, text, "gift", None, now)
        )
    for lesson in ("m1_l1", "m1_l2", "m1_l3"):
        await uow.tasks.save(Task(session.id, lesson, "t", "print", False, now))
    for lesson, outcome in [("m1_l1", "helped"), ("m1_l2", "partly"), ("m1_l3", "helped")]:
        await uow.checkins.add(Checkin(session.id, lesson, "yes", outcome, now))  # type: ignore[arg-type]
    other = uuid4()
    await uow.saved_phrases.add(SavedPhrase.create(uuid4(), other, "x", "gift", None, now))
    view = await use_case(uow, content, clock).execute(session)
    c = view.counts
    assert (c.scenarios_practised, c.phrases_saved, c.tasks_tried, c.tasks_helped) == (2, 2, 3, 2)
    scenarios = view.skills[0].scenarios
    assert scenarios is not None and (scenarios.practised, scenarios.best) == (2, 1)
    assert view.skills[0].roleplay is None


async def test_skills_confidence_day0_from_q11_and_first_vs_latest_sliders(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    day0 = await uow.confidence.get_day0(session.id)
    assert day0 is not None  # saved by CompleteQuiz from Q11
    view = await use_case(uow, content, clock).execute(session)
    assert view.confidence.day0 == day0 and view.confidence.first is None
    await uow.confidence.save_ratings(session.id, "first", {"repeat": 2, "refusal": 1})
    await uow.confidence.save_ratings(session.id, "latest", {"repeat": 4, "refusal": 3})
    view = await use_case(uow, content, clock).execute(session)
    assert view.confidence.first == {"repeat": 2, "refusal": 1}
    assert view.confidence.latest == {"repeat": 4, "refusal": 3}


async def test_skills_empty_state_for_new_subscriber_has_next_recommendation_with_reason(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await with_plan(uow, clock, content)
    view = await use_case(uow, content, clock).execute(session)
    assert view.skills == []
    assert (view.counts.scenarios_practised, view.counts.phrases_saved) == (0, 0)
    assert (view.counts.tasks_tried, view.counts.tasks_helped) == (0, 0)
    assert view.next is not None
    assert view.next.lesson_id == "m1_l1" and view.next.status == "available"
    assert view.next.reason and "{" not in view.next.reason
