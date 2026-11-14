"""Loading a run of the session."""

from uuid import UUID

from app.application.ports import UnitOfWork
from app.domain.roleplay.errors import RunNotFound
from app.domain.roleplay.run import RunRecord
from app.domain.session.entities import Session


async def load_run(uow: UnitOfWork, session: Session, run_id: UUID) -> RunRecord:
    """The run, or `RunNotFound` (also for another session's run, so ids cannot be probed)."""
    async with uow:
        record = await uow.roleplay_runs.get(run_id)
    if record is None or record.session_id != session.id:
        raise RunNotFound()
    return record


async def save_run(uow: UnitOfWork, record: RunRecord) -> None:
    async with uow:
        await uow.roleplay_runs.save(record)
        await uow.commit()
