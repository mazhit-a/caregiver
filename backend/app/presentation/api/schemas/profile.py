"""Profile request and response schemas. Unknown keys (diagnosis, medications, ...) are rejected;
the limits mirror `domain/profile`."""

from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints

from app.domain.profile import entities as limits
from app.presentation.api.schemas.base import CamelModel

Item = Annotated[str, StringConstraints(max_length=limits.MAX_ITEM_LENGTH)]
ItemList = list[Item]


class ContactIn(CamelModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=limits.MAX_CONTACT_NAME)
    phone: str = Field(min_length=1, max_length=limits.MAX_PHONE_LENGTH)
    role: str | None = Field(default=None, max_length=limits.MAX_CONTACT_ROLE)


class ProfileRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=limits.MAX_DISPLAY_NAME)
    enjoys: ItemList = Field(default_factory=list, max_length=limits.MAX_LIST_ITEMS)
    calms: ItemList = Field(default_factory=list, max_length=limits.MAX_LIST_ITEMS)
    avoid: ItemList = Field(default_factory=list, max_length=limits.MAX_LIST_ITEMS)
    rhythm: str = Field(default="", max_length=limits.MAX_RHYTHM_LENGTH)
    contacts: list[ContactIn] = Field(default_factory=list, max_length=limits.MAX_CONTACTS)
    caregiver_first_name: str | None = Field(default=None, max_length=limits.MAX_CAREGIVER_NAME)


class ContactOut(CamelModel):
    name: str
    phone: str
    role: str | None


class ProfileResponse(CamelModel):
    display_name: str | None
    enjoys: list[str]
    calms: list[str]
    avoid: list[str]
    rhythm: str
    contacts: list[ContactOut]
    caregiver_first_name: str | None
    updated_at: datetime | None
