from pydantic import Field, field_validator

from app.domain.events.catalog import MAX_BATCH_SIZE
from app.presentation.api.schemas.base import CamelModel

MAX_PROPS = 8
MAX_PROP_KEY = 40
MAX_PROP_STRING = 100


class EventIn(CamelModel):
    """Props with unknown keys, wrong types or sentence-like strings are dropped by the catalog;
    only the sizes are limited here (422)."""

    name: str = Field(min_length=1, max_length=40)
    props: dict[str, str | int | bool | None] = Field(default_factory=dict, max_length=MAX_PROPS)

    @field_validator("props")
    @classmethod
    def _limit_sizes(
        cls, props: dict[str, str | int | bool | None]
    ) -> dict[str, str | int | bool | None]:
        for key, value in props.items():
            if len(key) > MAX_PROP_KEY or (isinstance(value, str) and len(value) > MAX_PROP_STRING):
                raise ValueError("A prop key or value is too long.")
        return props


class EventsRequest(CamelModel):
    events: list[EventIn] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


class EventsResponse(CamelModel):
    stored: int
