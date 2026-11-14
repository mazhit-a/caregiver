"""Lesson routes (all behind the access gate)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.lessons.use_cases import GetLesson
from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.presentation.api.deps import SubscribedSession, get_clock, get_uow
from app.presentation.api.schemas.lessons import LessonProgressOut, LessonResponse, PatternOut

router = APIRouter(tags=["lessons"])


def _get_lesson(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetLesson:
    content: ContentProvider = request.app.state.content
    return GetLesson(uow, content, clock)


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
            "progress": LessonProgressOut(
                step=view.progress.step,
                started_at=view.progress.started_at,
                done_at=view.progress.done_at,
            ),
        }
    )
