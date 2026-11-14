"""Quiz routes. Answers can be health data: nothing here logs a request body."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.ports import ContentProvider, UnitOfWork
from app.application.quiz.use_cases import AnswerQuizQuestion, GetQuiz
from app.presentation.api.deps import CurrentSession, get_uow
from app.presentation.api.schemas.quiz import AnswerRequest, AnswerResponse, QuizResponse

router = APIRouter(prefix="/quiz", tags=["quiz"])


def _get_quiz(request: Request, uow: Annotated[UnitOfWork, Depends(get_uow)]) -> GetQuiz:
    content: ContentProvider = request.app.state.content
    return GetQuiz(uow, content)


def _answer_quiz_question(
    request: Request, uow: Annotated[UnitOfWork, Depends(get_uow)]
) -> AnswerQuizQuestion:
    content: ContentProvider = request.app.state.content
    return AnswerQuizQuestion(uow, content)


@router.get("", response_model=QuizResponse)
async def get_quiz(
    session: CurrentSession, use_case: Annotated[GetQuiz, Depends(_get_quiz)]
) -> QuizResponse:
    view = await use_case.execute(session)
    return QuizResponse(
        questions=view.questions,
        answers=view.answers,
        branch=view.branch,
        last_question_id=view.last_question_id,
        completed=view.completed,
        locked=view.locked,
    )


@router.put("/answers/{question_id}", response_model=AnswerResponse)
async def answer_question(
    question_id: str,
    body: AnswerRequest,
    session: CurrentSession,
    use_case: Annotated[AnswerQuizQuestion, Depends(_answer_quiz_question)],
) -> AnswerResponse:
    result = await use_case.execute(session, question_id, body.value)
    return AnswerResponse(
        question_id=result.question_id,
        branch=result.branch,
        tags=result.tags,
        last_question_id=result.last_question_id,
    )
