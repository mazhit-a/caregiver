"""The eval case model (one JSONL line) and its mapping to the production `CoachInput`."""

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.application.roleplay.dto import CoachInput, PreviousTurn

Source = Literal["package", "lesson", "generated"]
Mood = Literal["calmer", "same", "more_upset"]
Flag = Literal["medical", "crisis", "off_topic", "too_short"]
SAFETY_FLAGS: frozenset[str] = frozenset({"medical", "crisis"})


class _Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class ExpectedGoals(_Model):
    """Only the goals a case cares about; an unset goal is not checked."""

    notice: bool | None = None
    reassure: bool | None = None
    offer: bool | None = None


class Expect(_Model):
    """Expected result AFTER the domain rules. Unset fields are not checked.

    `score` is exact; `score_min` / `score_max` bound it. `parent_reaction == ""` means the rules
    must blank the parent line (medical, crisis).
    """

    goals: ExpectedGoals = ExpectedGoals()
    argued: bool | None = None
    score: int | None = Field(default=None, ge=0, le=3)
    score_min: int | None = Field(default=None, ge=0, le=3)
    score_max: int | None = Field(default=None, ge=0, le=3)
    parent_mood: Mood | None = None
    flags: tuple[Flag, ...] = ()
    parent_reaction: str | None = None


class PreviousTurnCase(_Model):
    parent: str
    caregiver: str
    score: int = Field(ge=0, le=3)


class EvalCase(_Model):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_\-.]+$")
    source: Source
    lesson_id: str | None = None
    label: str = "Mom"
    variant: str | None = "in_person"
    round: int = Field(ge=1)
    rounds_total: int = Field(default=3, ge=1)
    stage: str = ""
    parent_line: str
    parent_mood: str
    calms: tuple[str, ...] = ()
    previous_turns: tuple[PreviousTurnCase, ...] = ()
    caregiver_reply: str
    local_check: bool = False
    expect: Expect
    check_note: str | None = None

    def to_coach_input(self) -> CoachInput:
        """Exactly the production prompt contract (no extra fields reach the model)."""
        return CoachInput(
            label=self.label,
            variant=self.variant,
            round=self.round,
            rounds_total=self.rounds_total,
            stage=self.stage,
            parent_line=self.parent_line,
            parent_mood=self.parent_mood,
            calms=self.calms,
            previous_turns=tuple(
                PreviousTurn(parent=t.parent, caregiver=t.caregiver, score=t.score)
                for t in self.previous_turns
            ),
            caregiver_reply=self.caregiver_reply,
        )

    @property
    def stratum(self) -> str:
        """Coverage bucket for split summaries: the flag kind, or `scored`."""
        return self.expect.flags[0] if self.expect.flags else "scored"

    def to_json_line(self) -> str:
        return json.dumps(
            self.model_dump(by_alias=True, exclude_none=True, mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        )


def parse_case(raw: dict[str, Any]) -> EvalCase:
    return EvalCase.model_validate(raw)


def case_json_schema() -> dict[str, Any]:
    """The JSON schema of one dataset line (for editors and review tools)."""
    return EvalCase.model_json_schema(by_alias=True)
