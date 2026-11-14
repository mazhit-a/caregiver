"""The wording of the gentle exit (content/funnel-copy.json `gentleExit`)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GentleExitResourceCopy:
    id: str
    name: str
    description: str
    phone: str | None
    url: str | None


@dataclass(frozen=True)
class GentleExitCopy:
    title: str
    condolence: str
    resources_intro: str
    resources: tuple[GentleExitResourceCopy, ...]
    clear_data_confirmation: str
