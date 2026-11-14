"""`GET /api/funnel-copy`: the funnel strings, finished for this session. Read-only."""

from app.application.ports import Clock, ContentProvider, UnitOfWork
from app.domain.funnel.render import FunnelCopyView, render_funnel_copy
from app.domain.plan.errors import NoPlan
from app.domain.session.entities import Session


class GetFunnelCopy:
    def __init__(self, uow: UnitOfWork, content: ContentProvider, clock: Clock) -> None:
        self._uow = uow
        self._content = content
        self._clock = clock

    async def execute(self, session: Session) -> FunnelCopyView:
        async with self._uow:
            stored = await self._uow.plans.get(session.id)
        if stored is None or session.recipient_key is None:
            raise NoPlan()
        return render_funnel_copy(
            self._content.funnel_copy(),
            self._content.pricing(),
            self._content.recipient_labels(session.recipient_key),
            tuple(stored.plan.what_we_heard),
            session.app_today(self._clock.now()),
        )
