import asyncio
from copy import deepcopy
from uuid import UUID

from app.application.ports import CoachUnavailable
from app.application.roleplay.dto import CoachInput
from app.domain.roleplay.run import RunRecord
from app.domain.roleplay.verdict import CoachVerdict, Goals

PERFECT = CoachVerdict(
    goals=Goals(True, True, True),
    argued=False,
    flags=(),
    tip="That's all three steps.",
    better_phrase="You sound worried. I'm here. Want some tea?",
    parent_reaction="Tea sounds nice.",
    parent_mood="calmer",
)


class InMemoryRoleplayRunRepository:
    def __init__(self) -> None:
        self.rows: dict[UUID, RunRecord] = {}

    async def get(self, run_id: UUID) -> RunRecord | None:
        row = self.rows.get(run_id)
        return None if row is None else deepcopy(row)

    async def save(self, record: RunRecord) -> None:
        self.rows[record.id] = deepcopy(record)


class FakeCoach:
    """Scripted `Coach`: each item is a verdict to return or an exception to raise (use
    `CoachUnavailable` for timeout, API error, refusal and invalid JSON alike). Once the script
    is used up it returns `default`. With a `gate`, every call waits for it (never set it to
    simulate a hang). `calls` holds the exact `CoachInput` objects received."""

    def __init__(
        self,
        *script: CoachVerdict | Exception,
        default: CoachVerdict = PERFECT,
        gate: asyncio.Event | None = None,
    ) -> None:
        self._script = list(script)
        self._default = default
        self.gate = gate
        self.calls: list[CoachInput] = []
        self._entered = asyncio.Condition()

    async def turn(self, coach_input: CoachInput) -> CoachVerdict:
        self.calls.append(coach_input)
        async with self._entered:
            self._entered.notify_all()
        if self.gate is not None:
            await self.gate.wait()
        item = self._script.pop(0) if self._script else self._default
        if isinstance(item, Exception):
            raise item
        return item

    async def wait_for_calls(self, count: int) -> None:
        """Return once `count` calls have started (no sleeping)."""
        async with self._entered:
            await self._entered.wait_for(lambda: len(self.calls) >= count)


def unavailable() -> CoachUnavailable:
    return CoachUnavailable("scripted failure")
