"""Use case: list the public crisis resources (no session needed)."""

from dataclasses import dataclass

from app.application.ports import ContentProvider
from app.domain.safety.resources import CrisisResource


@dataclass(frozen=True)
class CrisisResourcesResult:
    resources: list[CrisisResource]
    verify_before_launch: bool


class ListCrisisResources:
    def __init__(self, content: ContentProvider) -> None:
        self._content = content

    def execute(self) -> CrisisResourcesResult:
        return CrisisResourcesResult(
            resources=self._content.crisis_resources(),
            verify_before_launch=self._content.crisis_resources_need_verification(),
        )
