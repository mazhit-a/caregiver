"""Skills progress route (behind the access gate)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.application.skills.use_cases import GetSkills
from app.presentation.api.deps import SubscribedSession, get_clock, get_uow
from app.presentation.api.schemas.skills import (
    ConfidenceOut,
    CountsOut,
    NextLessonOut,
    RoleplayProgressOut,
    ScenarioProgressOut,
    SkillOut,
    SkillsResponse,
)

router = APIRouter(tags=["skills"])


def _get_skills(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetSkills:
    content: ContentProvider = request.app.state.content
    return GetSkills(uow, content, clock)


@router.get("/skills", response_model=SkillsResponse)
async def get_skills(
    session: SubscribedSession, use_case: Annotated[GetSkills, Depends(_get_skills)]
) -> SkillsResponse:
    view = await use_case.execute(session)
    nxt = view.next
    return SkillsResponse(
        skills=[
            SkillOut(
                id=s.id,
                label=s.label,
                roleplay=None
                if s.roleplay is None
                else RoleplayProgressOut(
                    runs=s.roleplay.runs,
                    first_score=s.roleplay.first_score,
                    latest_score=s.roleplay.latest_score,
                    max_score=s.roleplay.max_score,
                ),
                scenarios=None
                if s.scenarios is None
                else ScenarioProgressOut(practised=s.scenarios.practised, best=s.scenarios.best),
            )
            for s in view.skills
        ],
        confidence=ConfidenceOut(
            day0=view.confidence.day0, first=view.confidence.first, latest=view.confidence.latest
        ),
        counts=CountsOut(
            scenarios_practised=view.counts.scenarios_practised,
            phrases_saved=view.counts.phrases_saved,
            tasks_tried=view.counts.tasks_tried,
            tasks_helped=view.counts.tasks_helped,
        ),
        next=None
        if nxt is None
        else NextLessonOut(
            lesson_id=nxt.lesson_id,
            title=nxt.title,
            module_id=nxt.module_id,
            reason=nxt.reason,
            status=nxt.status,
            unlock_on=nxt.unlock_on,
        ),
    )
