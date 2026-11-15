from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.billing.dto import StartRequest
from app.application.billing.use_cases import (
    CheckAccess,
    GetPricing,
    StartDemoSubscription,
    StartSubscription,
)
from app.application.plan.use_cases import CompleteQuiz
from app.application.quiz.use_cases import AnswerQuizQuestion
from app.domain.billing.errors import AccessDenied, AlreadySubscribed, ConsentRequired
from app.domain.plan.errors import NoPlan
from app.domain.quiz.errors import QuizLocked
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.application.plan.test_plan_use_cases import PERSONA_A
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

REPO = Path(__file__).resolve().parents[4]
ANSWERS = {**PERSONA_A, "q5_changes": ["repeats", "evenings"]}


@pytest.fixture(scope="module")
def content() -> JsonContentProvider:
    return JsonContentProvider.from_directory(REPO / "content")


async def _session(uow: FakeUnitOfWork, clock: FixedClock, offset: timedelta) -> Session:
    session = Session(uuid4(), "h", "UTC", offset, clock.now(), clock.now())
    await uow.sessions.add(session)
    return session


async def _with_plan(
    uow: FakeUnitOfWork,
    clock: FixedClock,
    content: JsonContentProvider,
    offset: timedelta = timedelta(0),
) -> Session:
    session = await _session(uow, clock, offset)
    answer = AnswerQuizQuestion(uow, content)
    for question, value in ANSWERS.items():
        await answer.execute(session, question, value)
    await CompleteQuiz(uow, content, clock).execute(session)
    return session


def demo_request() -> StartRequest:
    return StartRequest("demo", auto_renew_consent=True)


async def test_start_records_history_with_app_now_and_source(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _with_plan(uow, clock, content, offset=timedelta(days=2))
    await StartSubscription(uow, content, clock).execute(session, demo_request())
    [entry] = await uow.subscription_history.list_for_session(session.id)
    assert entry.at == clock.now() + timedelta(days=2)
    assert (entry.source, entry.from_status, entry.to_status) == ("demo", "none", "demo")


async def test_start_subscription_called_twice_is_a_no_op_second_time(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _with_plan(uow, clock, content)
    start = StartSubscription(uow, content, clock)
    first = await start.execute(session, demo_request())
    purged_at = (await uow.quiz.get(session.id)).health_answers_purged_at  # type: ignore[union-attr]
    clock.advance(timedelta(days=1))
    saves_before = len(uow.subscriptions.saves)
    second = await start.execute(session, demo_request())
    assert second.status == first.status == "demo"
    assert second.current_period_end == first.current_period_end
    assert len(uow.subscriptions.saves) == saves_before
    assert len(await uow.subscription_history.list_for_session(session.id)) == 1
    schedule = await uow.lesson_schedule.list_for_session(session.id)
    assert len(schedule) == len({s.lesson_id for s in schedule}) > 0
    assert (await uow.quiz.get(session.id)).health_answers_purged_at == purged_at  # type: ignore[union-attr]


async def test_consent_timestamp_stored_before_status_change(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _with_plan(uow, clock, content)
    await StartSubscription(uow, content, clock).execute(session, demo_request())
    first_save, second_save = uow.subscriptions.saves
    assert first_save.status == "none"
    assert first_save.auto_renew_consent_at == clock.now()
    assert second_save.status == "demo"


async def test_start_without_consent_changes_nothing(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _with_plan(uow, clock, content)
    demo = StartDemoSubscription(uow, StartSubscription(uow, content, clock))
    with pytest.raises(ConsentRequired):
        await demo.execute(session, False, None)
    with pytest.raises(ConsentRequired):
        await StartSubscription(uow, content, clock).execute(
            session, StartRequest("demo", auto_renew_consent=False)
        )
    assert uow.subscriptions.saves == []
    assert uow.subscription_history.entries == []


async def test_start_without_plan_raises_no_plan(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock, timedelta(0))
    with pytest.raises(NoPlan):
        await StartSubscription(uow, content, clock).execute(session, demo_request())


async def test_start_creates_schedule_and_purges_q3_q5_and_locks_quiz(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _with_plan(uow, clock, content, offset=timedelta(days=1))
    stored = await uow.plans.get(session.id)
    assert stored is not None
    before = await uow.quiz.get(session.id)
    assert before is not None and "q3_situation" in before.answers
    await StartSubscription(uow, content, clock).execute(session, demo_request())
    quiz = await uow.quiz.get(session.id)
    assert quiz is not None
    assert quiz.locked and quiz.health_answers_purged_at is not None
    assert "q3_situation" not in quiz.answers and "q5_changes" not in quiz.answers
    assert "q6_living" in quiz.answers
    assert quiz.tags == before.tags and quiz.branch == before.branch
    assert await uow.plans.get(session.id) == stored
    schedule = await uow.lesson_schedule.list_for_session(session.id)
    built = [lesson.id for m in stored.plan.modules for lesson in m.lessons if lesson.built]
    assert [s.lesson_id for s in schedule] == built
    assert schedule[0].unlock_on == date(2026, 1, 6)  # app today = real day + 1
    with pytest.raises(QuizLocked):
        await AnswerQuizQuestion(uow, content).execute(session, "q6_living", "far")


async def test_demo_start_on_existing_subscription_raises_already_subscribed(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _with_plan(uow, clock, content)
    demo = StartDemoSubscription(uow, StartSubscription(uow, content, clock))
    await demo.execute(session, True, None)
    with pytest.raises(AlreadySubscribed):
        await demo.execute(session, True, None)


async def test_pricing_first_renewal_date_is_app_today_plus_intro_days(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock, timedelta(days=3))
    view = GetPricing(content, clock).execute(session)
    today = date(2026, 1, 8)
    by_id = {p.id: p for p in view.plans}
    assert by_id["four_week"].first_renewal_date == today + timedelta(days=28)
    assert by_id["twelve_week"].first_renewal_date == today + timedelta(days=84)
    assert view.default_plan_id == "four_week"
    assert str(by_id["four_week"].price_today) == "19.99"
    assert str(by_id["four_week"].renewal_price) == "39.99"


async def test_check_access_uses_plan_presence_for_status_none(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock, timedelta(0))
    check = CheckAccess(uow, clock)
    with pytest.raises(AccessDenied) as no_plan:
        await check.execute(session)
    assert no_plan.value.reason == "no_plan"
    answer = AnswerQuizQuestion(uow, content)
    for question, value in ANSWERS.items():
        await answer.execute(session, question, value)
    await CompleteQuiz(uow, content, clock).execute(session)
    with pytest.raises(AccessDenied) as no_sub:
        await check.execute(session)
    assert no_sub.value.reason == "no_subscription"
    await StartSubscription(uow, content, clock).execute(session, demo_request())
    await check.execute(session)
