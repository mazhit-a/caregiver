"""Session routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.session.use_cases import CreateSession
from app.presentation.api.deps import get_create_session, limit_session_creation
from app.presentation.api.schemas.base import CamelModel

router = APIRouter()


class CreateSessionRequest(CamelModel):
    timezone: str | None = None


class CreateSessionResponse(CamelModel):
    token: str
    timezone: str


@router.post(
    "/session",
    response_model=CreateSessionResponse,
    status_code=201,
    dependencies=[Depends(limit_session_creation)],
)
async def create_session(
    use_case: Annotated[CreateSession, Depends(get_create_session)],
    body: CreateSessionRequest | None = None,
) -> CreateSessionResponse:
    created = await use_case.execute(body.timezone if body else None)
    return CreateSessionResponse(token=created.token, timezone=created.session.timezone)
