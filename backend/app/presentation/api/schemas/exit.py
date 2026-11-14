"""Gentle exit and clear-data response schemas."""

from app.presentation.api.schemas.base import CamelModel


class GrieveResourceOut(CamelModel):
    id: str
    name: str
    description: str
    phone: str | None
    url: str | None


class GentleExitResponse(CamelModel):
    title: str
    condolence: str
    resources_intro: str
    resources: list[GrieveResourceOut]


class ClearDataResponse(CamelModel):
    message: str
