"""DTOs of the plan use cases."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.plan.entities import BuiltPlan


@dataclass(frozen=True)
class CompleteResult:
    completed_at: datetime
    rules_version: int
    content_version: str


@dataclass(frozen=True)
class PlanPreviewView:
    plan: BuiltPlan
    rules_version: int
    content_version: str
    built_at: datetime


@dataclass(frozen=True)
class GiftPhrase:
    id: str
    text: str
    when: str


@dataclass(frozen=True)
class GiftSheet:
    title: str
    intro: str
    phrases: list[GiftPhrase]
    footer: str
