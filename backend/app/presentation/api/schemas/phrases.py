"""Saved phrase request and response schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.presentation.api.schemas.base import CamelModel


class SavePhraseRequest(CamelModel):
    text: str = Field(min_length=1, max_length=300)
    source: Literal["scenario", "roleplay", "gift"]
    lesson_id: str | None = Field(default=None, min_length=1, max_length=64)


class PhraseOut(CamelModel):
    id: UUID
    text: str
    source: Literal["scenario", "roleplay", "gift"]
    lesson_id: str | None
    saved_at: datetime


class PhrasesResponse(CamelModel):
    phrases: list[PhraseOut]
