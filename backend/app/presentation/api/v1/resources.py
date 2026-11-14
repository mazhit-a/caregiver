"""Public resources routes (no session, no gate)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.ports import ContentProvider
from app.application.resources.list_crisis_resources import ListCrisisResources
from app.presentation.api.schemas.base import CamelModel

router = APIRouter(prefix="/resources", tags=["resources"])


class CrisisResourceSchema(CamelModel):
    id: str
    name: str
    phone: str
    description: str


class CrisisResourcesResponse(CamelModel):
    resources: list[CrisisResourceSchema]
    verify_before_launch: bool


def _list_crisis_resources(request: Request) -> ListCrisisResources:
    content: ContentProvider = request.app.state.content
    return ListCrisisResources(content)


@router.get("/crisis", response_model=CrisisResourcesResponse)
async def get_crisis_resources(
    use_case: Annotated[ListCrisisResources, Depends(_list_crisis_resources)],
) -> CrisisResourcesResponse:
    result = use_case.execute()
    return CrisisResourcesResponse(
        resources=[
            CrisisResourceSchema(id=r.id, name=r.name, phone=r.phone, description=r.description)
            for r in result.resources
        ],
        verify_before_launch=result.verify_before_launch,
    )
