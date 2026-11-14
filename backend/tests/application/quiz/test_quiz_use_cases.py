import json
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.quiz.use_cases import AnswerQuizQuestion, GetQuiz
from app.domain.quiz.errors import QuizLocked
from app.domain.session.entities import Session
from app.infrastructure.content.provider import JsonContentProvider
from tests.fakes.clock import FixedClock
from tests.fakes.unit_of_work import FakeUnitOfWork

REPO = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def content() -> JsonContentProvider:
    return JsonContentProvider.from_directory(REPO / "content")


async def _session(uow: FakeUnitOfWork) -> Session:
    now = FixedClock().now()
    session = Session(uuid4(), "h", "UTC", timedelta(0), now, now)
    await uow.sessions.add(session)
    return session


async def test_resume_returns_saved_answers_and_last_question_id(
    uow: FakeUnitOfWork, content: JsonContentProvider
) -> None:
    session = await _session(uow)
    answer = AnswerQuizQuestion(uow, content)
    await answer.execute(session, "q1_recipient", "dad")
    await answer.execute(session, "q2_age", "85plus")
    await answer.execute(session, "q3_situation", "noticing")
    view = await GetQuiz(uow, content).execute(session)
    assert view.answers == {"q1_recipient": "dad", "q2_age": "85plus", "q3_situation": "noticing"}
    assert view.last_question_id == "q3_situation"
    assert view.branch == "noticing"
    assert not view.completed


async def test_answering_q1_sets_session_recipient_key(
    uow: FakeUnitOfWork, content: JsonContentProvider
) -> None:
    session = await _session(uow)
    await AnswerQuizQuestion(uow, content).execute(session, "q1_recipient", "in_law")
    stored = uow.sessions.rows[session.id]
    assert stored.recipient_key == "in_law"
    assert uow.committed


async def test_locked_quiz_raises_and_saves_nothing(
    uow: FakeUnitOfWork, content: JsonContentProvider
) -> None:
    session = await _session(uow)
    await AnswerQuizQuestion(uow, content).execute(session, "q1_recipient", "mom")
    uow.quiz.rows[session.id].locked = True
    with pytest.raises(QuizLocked):
        await AnswerQuizQuestion(uow, content).execute(session, "q2_age", "65_74")
    assert "q2_age" not in uow.quiz.rows[session.id].answers


@pytest.mark.parametrize("key", ["mom", "dad", "both", "in_law", "other", None])
async def test_get_quiz_renders_labels_from_q1_with_no_leftover_placeholder(
    uow: FakeUnitOfWork, content: JsonContentProvider, key: str | None
) -> None:
    session = await _session(uow)
    session.recipient_key = key
    view = await GetQuiz(uow, content).execute(session)
    text = json.dumps(view.questions)
    assert not re.search(r"\{\w+\}", text)  # no placeholder left
    assert not [s for s in _strings(view.questions) if "{" in s or "}" in s]
    types = [q["type"] for q in view.questions]
    assert types.count("interstitial") == 2
    ids = [q["id"] for q in view.questions]
    assert ids[ids.index("q5_changes") + 1] == "reassure_1"
    assert ids[ids.index("q9_worries") + 1] == "reassure_2"
    if key == "both":
        assert "your parents" in text
    if key == "mom":
        assert "How old is Mom?" in text


async def test_get_quiz_hides_rules_and_picks_branch_subtitle(
    uow: FakeUnitOfWork, content: JsonContentProvider
) -> None:
    session = await _session(uow)
    await AnswerQuizQuestion(uow, content).execute(session, "q3_situation", "noticing")
    view = await GetQuiz(uow, content).execute(session)
    q5 = next(q for q in view.questions if q["id"] == "q5_changes")
    assert q5["subtitle"] == "Pick up to 3. It's okay if you're not sure yet."
    assert "subtitleByBranch" not in q5 and q5["healthData"] is True
    assert not re.search(r"tags|derivedTags|usedFor|heard", json.dumps(view.questions))


def _strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [s for item in node for s in _strings(item)]
    if isinstance(node, dict):
        return [s for item in node.values() for s in _strings(item)]
    return []
