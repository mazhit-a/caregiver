"""App copy route: finished, recipient-aware strings. Session only, not gated."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.app_copy.use_cases import GetAppCopy
from app.application.ports import ContentProvider
from app.presentation.api.deps import CurrentSession
from app.presentation.api.schemas.app_copy import AppCopyResponse

router = APIRouter(tags=["app-copy"])


def _get_app_copy(request: Request) -> GetAppCopy:
    content: ContentProvider = request.app.state.content
    return GetAppCopy(content)


@router.get("/app-copy", response_model=AppCopyResponse)
async def app_copy(
    session: CurrentSession, use_case: Annotated[GetAppCopy, Depends(_get_app_copy)]
) -> AppCopyResponse:
    return AppCopyResponse.model_validate(await use_case.execute(session))
