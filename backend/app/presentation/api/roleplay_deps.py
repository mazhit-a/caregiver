"""Dependencies of the role-play routes: coach, limiters and the turn use case.

`app.state.coach`, `app.state.rate_limiter` and `app.state.llm_limiter` are set once in
`main.create_app` (one limiter instance per process).
"""

from typing import Annotated

from fastapi import Depends, Request

from app.application.ports import Clock, Coach, ContentProvider, RateLimiter, UnitOfWork
from app.application.roleplay.limiter import LlmConcurrencyLimiter
from app.application.roleplay.turn import SubmitRoleplayTurn
from app.presentation.api.deps import get_clock, get_uow


def get_content(request: Request) -> ContentProvider:
    content: ContentProvider = request.app.state.content
    return content


def get_coach(request: Request) -> Coach:
    coach: Coach = request.app.state.coach
    return coach


def get_rate_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.rate_limiter
    return limiter


def get_llm_limiter(request: Request) -> LlmConcurrencyLimiter:
    limiter: LlmConcurrencyLimiter = request.app.state.llm_limiter
    return limiter


def get_llm_deadline(request: Request) -> float:
    deadline: float = request.app.state.settings.llm_timeout_seconds
    return deadline


def get_coach_turn_use_case(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    content: Annotated[ContentProvider, Depends(get_content)],
    coach: Annotated[Coach, Depends(get_coach)],
    clock: Annotated[Clock, Depends(get_clock)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    llm_limiter: Annotated[LlmConcurrencyLimiter, Depends(get_llm_limiter)],
    deadline: Annotated[float, Depends(get_llm_deadline)],
) -> SubmitRoleplayTurn:
    return SubmitRoleplayTurn(uow, content, coach, clock, rate_limiter, llm_limiter, deadline)
