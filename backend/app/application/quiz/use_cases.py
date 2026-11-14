"""Quiz use cases: read the quiz with saved answers, save one answer."""

from typing import Any

from app.application.ports import ContentProvider, UnitOfWork
from app.application.quiz.dto import AnswerResult, QuizView
from app.domain.quiz.definition import RECIPIENT_QUESTION_ID, QuestionSpec
from app.domain.quiz.entities import QuizState
from app.domain.session.entities import Session
from app.domain.shared.labels import RecipientLabels, render_tree

# Neutral wording until Q1 is answered ("your loved one").
_NEUTRAL_RECIPIENT_KEY = "other"


class GetQuiz:
    def __init__(self, uow: UnitOfWork, content: ContentProvider) -> None:
        self._uow = uow
        self._content = content

    async def execute(self, session: Session) -> QuizView:
        async with self._uow:
            state = await self._uow.quiz.get(session.id) or QuizState(session.id)
        key = session.recipient_key or _NEUTRAL_RECIPIENT_KEY
        labels = self._content.recipient_labels(key)
        questions = [
            _render(spec, labels, state.branch)
            for spec in self._content.quiz_definition().questions
        ]
        return QuizView(
            questions=questions,
            answers=state.answers,
            branch=state.branch,
            last_question_id=state.last_question_id,
            completed=state.completed_at is not None,
            locked=state.locked,
        )


def _render(spec: QuestionSpec, labels: RecipientLabels, branch: str | None) -> dict[str, Any]:
    display = dict(spec.display)
    by_branch = display.pop("subtitleByBranch", None)
    if branch and isinstance(by_branch, dict) and branch in by_branch:
        display["subtitle"] = by_branch[branch]
    rendered = dict(render_tree(display, labels))  # type: ignore[call-overload]
    return {**rendered, "healthData": spec.health_data}


class AnswerQuizQuestion:
    def __init__(self, uow: UnitOfWork, content: ContentProvider) -> None:
        self._uow = uow
        self._content = content

    async def execute(self, session: Session, question_id: str, value: Any) -> AnswerResult:
        definition = self._content.quiz_definition()
        async with self._uow:
            state = await self._uow.quiz.get(session.id) or QuizState(session.id)
            state.answer(definition, question_id, value)
            await self._uow.quiz.save(state)
            if question_id == RECIPIENT_QUESTION_ID:
                session.recipient_key = state.answers[question_id]
                await self._uow.sessions.save(session)
            await self._uow.commit()
        return AnswerResult(question_id, state.branch, state.tags, state.last_question_id)
