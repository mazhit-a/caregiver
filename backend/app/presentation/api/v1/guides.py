"""Public quick-guide routes: no gate, no subscription check. A session token (optional)
only personalises the wording; an unknown token is a 401 like `GET /pricing`."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.guides.use_cases import GetGuide, ListGuides
from app.application.ports import ContentProvider
from app.presentation.api.deps import OptionalSession
from app.presentation.api.schemas.guides import (
    GuideListResponse,
    GuideResponse,
    GuideSummaryOut,
)

router = APIRouter(prefix="/guides", tags=["guides"])


def _content(request: Request) -> ContentProvider:
    content: ContentProvider = request.app.state.content
    return content


ContentDep = Annotated[ContentProvider, Depends(_content)]


@router.get("", response_model=GuideListResponse)
async def list_guides(session: OptionalSession, content: ContentDep) -> GuideListResponse:
    guides = ListGuides(content).execute(session)
    return GuideListResponse(
        guides=[
            GuideSummaryOut(id=g.id, title=g.title, summary=g.summary, urgency=g.urgency)
            for g in guides
        ]
    )


@router.get("/{guide_id}", response_model=GuideResponse)
async def get_guide(guide_id: str, session: OptionalSession, content: ContentDep) -> GuideResponse:
    return GuideResponse.from_rendered(GetGuide(content).execute(guide_id, session))
