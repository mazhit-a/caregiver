"""Check-in request and response schemas."""

from typing import Literal

from pydantic import Field

from app.presentation.api.schemas.base import CamelModel


class DoctorNoteIn(CamelModel):
    add_to_visit_sheet: bool
    text: str | None = Field(default=None, max_length=300)


class CheckinRequest(CamelModel):
    plan_id: str = Field(min_length=1, max_length=64)
    came_up: str = Field(min_length=1, max_length=32)
    outcome: Literal["helped", "partly", "didnt_help"] | None = None
    doctor_note: DoctorNoteIn | None = None


class FollowUpOut(CamelModel):
    title: str
    text: str


class PlanQuoteOut(CamelModel):
    cue: str
    response: str
    reset: str | None


class CheckinResponse(CamelModel):
    plan_id: str
    came_up: str
    outcome: Literal["helped", "partly", "didnt_help"] | None
    response_text: str | None
    follow_ups: list[FollowUpOut]
    plan: PlanQuoteOut
    observation_added: bool
    task_done: bool
