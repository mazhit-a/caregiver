"""Lesson routes (all behind the access gate)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.lessons.answer import AnswerLesson
from app.application.lessons.complete import CompleteLesson
from app.application.lessons.progress import SaveLessonStep
from app.application.lessons.use_cases import GetLesson
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.presentation.api.deps import SubscribedSession, get_clock, get_uow
from app.presentation.api.schemas.lessons import (
    AnswerRequest,
    AnswerResponse,
    CompleteResponse,
    LessonProgressOut,
    LessonResponse,
    NextLessonOut,
    PatternOut,
    RecapOut,
    StepRequest,
)

router = APIRouter(tags=["lessons"])


def _get_lesson(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetLesson:
    content: ContentProvider = request.app.state.content
    return GetLesson(uow, content, clock)


def _answer_lesson(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AnswerLesson:
    content: ContentProvider = request.app.state.content
    return AnswerLesson(
        uow, content, clock, public_app_url=request.app.state.settings.public_app_url
    )


def _complete_lesson(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> CompleteLesson:
    content: ContentProvider = request.app.state.content
    return CompleteLesson(uow, content, clock)


def _save_step(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> SaveLessonStep:
    content: ContentProvider = request.app.state.content
    return SaveLessonStep(uow, content, clock)


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: str,
    session: SubscribedSession,
    use_case: Annotated[GetLesson, Depends(_get_lesson)],
) -> LessonResponse:
    view = await use_case.execute(session, lesson_id)
    lesson = view.lesson
    return LessonResponse.model_validate(
        {
            "id": lesson.id,
            "moduleId": lesson.module_id,
            "title": lesson.title,
            "minutes": lesson.minutes,
            "skill": lesson.skill,
            "skillLabel": lesson.skill_label,
            "variant": lesson.variant,
            "unlockOn": view.unlock_on,
            "pattern": PatternOut.model_validate(lesson.pattern),
            "screens": lesson.screens,
            "screenCount": view.screen_count,
            "progress": LessonProgressOut(
                step=view.progress.step,
                started_at=view.progress.started_at,
                done_at=view.progress.done_at,
            ),
            "recap": None
            if view.recap is None
            else RecapOut(from_lesson_id=view.recap.from_lesson_id, text=view.recap.text),
        }
    )


@router.post("/lessons/{lesson_id}/answers", response_model=AnswerResponse)
async def answer_lesson(
    lesson_id: str,
    body: AnswerRequest,
    session: SubscribedSession,
    use_case: Annotated[AnswerLesson, Depends(_answer_lesson)],
) -> AnswerResponse:
    view = await use_case.execute(session, lesson_id, body.screen_id, body.value)
    return AnswerResponse(screen_id=view.screen_id, type=view.screen_type, result=view.result)


@router.post("/lessons/{lesson_id}/complete", response_model=CompleteResponse)
async def complete_lesson(
    lesson_id: str,
    session: SubscribedSession,
    use_case: Annotated[CompleteLesson, Depends(_complete_lesson)],
) -> CompleteResponse:
    view = await use_case.execute(session, lesson_id)
    nxt = view.next_lesson
    return CompleteResponse.model_validate(
        {
            "lessonId": view.lesson_id,
            "doneAt": view.done_at,
            "wrap": view.wrap,
            "nextLesson": None
            if nxt is None
            else NextLessonOut(
                id=nxt.lesson_id,
                title=nxt.title,
                module_id=nxt.module_id,
                reason=nxt.reason,
                unlock_on=nxt.unlock_on,
            ),
            "allDoneLine": view.all_done_line,
        }
    )


@router.put("/lessons/{lesson_id}/progress", response_model=LessonProgressOut)
async def save_lesson_step(
    lesson_id: str,
    body: StepRequest,
    session: SubscribedSession,
    use_case: Annotated[SaveLessonStep, Depends(_save_step)],
) -> LessonProgressOut:
    view = await use_case.execute(session, lesson_id, body.step)
    return LessonProgressOut(step=view.step, started_at=view.started_at, done_at=view.done_at)
