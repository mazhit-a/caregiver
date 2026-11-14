from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.application.plan.use_cases import CompleteQuiz, GetGiftSheet, GetPlanPreview
from app.application.quiz.use_cases import AnswerQuizQuestion
from app.domain.plan.errors import NoPlan
from app.domain.quiz.errors import QuizIncomplete, QuizLocked
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

REPO = Path(__file__).resolve().parents[4]

PERSONA_A: dict[str, Any] = {
    "q1_recipient": "dad",
    "q2_age": "65_74",
    "q3_situation": "noticing",
    "q6_living": "nearby",
    "q7_helpers": "siblings",
    "q8_work": "part_time",
    "q9_worries": ["future"],
    "q10_documents": {"healthcare_proxy": "have", "financial_poa": "have", "hipaa_release": "have"},
    "q11_confidence": 3,
    "q12_time": "5",
}


@pytest.fixture(scope="module")
def content() -> JsonContentProvider:
    return JsonContentProvider.from_directory(REPO / "content")


async def _session(uow: FakeUnitOfWork, clock: FixedClock) -> Session:
    session = Session(uuid4(), "h", "UTC", timedelta(0), clock.now(), clock.now())
    await uow.sessions.add(session)
    return session


async def _answer_all(uow: FakeUnitOfWork, content: JsonContentProvider, session: Session) -> None:
    answer = AnswerQuizQuestion(uow, content)
    for question, value in PERSONA_A.items():
        await answer.execute(session, question, value)


async def test_complete_builds_and_stores_plan_with_q5_skipped(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock)
    await _answer_all(uow, content, session)
    result = await CompleteQuiz(uow, content, clock).execute(session)
    stored = uow.plans.rows[session.id]
    assert stored.built_at == clock.now() == result.completed_at
    assert stored.plan.modules[1].id == "m0_before"  # noticing branch
    assert stored.lessons_per_week == 3
    assert len(stored.gift_phrase_ids) == 5
    assert uow.confidence.day0[session.id] == 3
    assert uow.quiz.rows[session.id].completed_at == clock.now()
    assert uow.committed


async def test_incomplete_quiz_lists_missing_and_stores_nothing(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock)
    with pytest.raises(QuizIncomplete) as exc:
        await CompleteQuiz(uow, content, clock).execute(session)
    assert "q1_recipient" in exc.value.details["questionIds"]
    assert not uow.plans.rows and not uow.confidence.day0


async def test_locked_quiz_never_touches_stored_plan(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock)
    await _answer_all(uow, content, session)
    complete = CompleteQuiz(uow, content, clock)
    await complete.execute(session)
    plan = uow.plans.rows[session.id]
    uow.quiz.rows[session.id].locked = True
    clock.advance(timedelta(days=1))
    with pytest.raises(QuizLocked):
        await complete.execute(session)
    assert uow.plans.rows[session.id] is plan


async def test_preview_and_gift_without_plan_raise_no_plan(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock)
    with pytest.raises(NoPlan) as exc:
        await GetPlanPreview(uow).execute(session)
    assert exc.value.details == {"reason": "no_plan"}
    with pytest.raises(NoPlan):
        await GetGiftSheet(uow, content).execute(session)


async def test_gift_for_persona_a_pads_to_five_phrases(
    uow: FakeUnitOfWork, clock: FixedClock, content: JsonContentProvider
) -> None:
    session = await _session(uow, clock)
    await _answer_all(uow, content, session)
    await CompleteQuiz(uow, content, clock).execute(session)
    sheet = await GetGiftSheet(uow, content).execute(session)
    assert len(sheet.phrases) == 5
    assert sheet.title == "Phrases that calm Dad"
