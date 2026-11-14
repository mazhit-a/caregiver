"""Mom's page routes (behind the access gate). Bodies hold family data: never logged."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.ports import Clock, UnitOfWork
from app.application.profile.use_cases import GetProfile, ProfileInput, ProfileView, UpdateProfile
from app.domain.profile.entities import Contact
from app.presentation.api.deps import SubscribedSession, get_clock, get_uow
from app.presentation.api.schemas.profile import ContactOut, ProfileRequest, ProfileResponse

router = APIRouter(tags=["profile"])


def _get(
    uow: Annotated[UnitOfWork, Depends(get_uow)], clock: Annotated[Clock, Depends(get_clock)]
) -> GetProfile:
    return GetProfile(uow, clock)


def _update(
    uow: Annotated[UnitOfWork, Depends(get_uow)], clock: Annotated[Clock, Depends(get_clock)]
) -> UpdateProfile:
    return UpdateProfile(uow, clock)


def _out(view: ProfileView) -> ProfileResponse:
    p = view.profile
    return ProfileResponse(
        display_name=view.display_name,
        enjoys=list(p.enjoys),
        calms=list(p.calms),
        avoid=list(p.avoid),
        rhythm=p.rhythm,
        contacts=[ContactOut(name=c.name, phone=c.phone, role=c.role) for c in p.contacts],
        caregiver_first_name=p.caregiver_first_name,
        updated_at=p.updated_at if view.exists else None,
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    session: SubscribedSession, use_case: Annotated[GetProfile, Depends(_get)]
) -> ProfileResponse:
    return _out(await use_case.execute(session))


@router.put("/profile", response_model=ProfileResponse)
async def put_profile(
    body: ProfileRequest,
    session: SubscribedSession,
    use_case: Annotated[UpdateProfile, Depends(_update)],
) -> ProfileResponse:
    data = ProfileInput(
        body.display_name,
        tuple(body.enjoys),
        tuple(body.calms),
        tuple(body.avoid),
        body.rhythm,
        tuple(Contact(c.name, c.phone, c.role) for c in body.contacts),
        body.caregiver_first_name,
    )
    return _out(await use_case.execute(session, data))
