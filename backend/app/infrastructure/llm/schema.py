"""Response schema of the coach call (the OUTPUT contract of `roleplay-turn.v1.md`).

Strict: unknown keys, flags or moods fail validation, which the adapter turns into
`CoachUnavailable`. `score` is read only so the contract stays complete: the domain recomputes it.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.domain.roleplay.verdict import CoachVerdict, Goals, validate_verdict


class _Strict(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class GoalsOut(_Strict):
    notice: bool
    reassure: bool
    offer: bool


class CoachResponse(_Strict):
    goals: GoalsOut
    argued: bool
    score: int
    tip: str
    better_phrase: str
    parent_reaction: str
    parent_mood: Literal["calmer", "same", "more_upset"]
    flags: list[Literal["medical", "crisis", "off_topic", "too_short"]]

    def to_verdict(self) -> CoachVerdict:
        """The model's raw judgement; `validate_verdict` re-checks flags and mood (defence)."""
        return validate_verdict(
            CoachVerdict(
                goals=Goals(self.goals.notice, self.goals.reassure, self.goals.offer),
                argued=self.argued,
                flags=tuple(self.flags),
                tip=self.tip,
                better_phrase=self.better_phrase,
                parent_reaction=self.parent_reaction,
                parent_mood=self.parent_mood,
            )
        )
