"""Shared base for API schemas: camelCase JSON, snake_case Python."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ErrorBody(CamelModel):
    code: str
    message: str
    details: dict[str, object]


class ErrorResponse(CamelModel):
    error: ErrorBody
