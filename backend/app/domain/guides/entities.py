"""Quick guides: short how-tos for urgent moments (content/quick-guides.json). Pure."""

from dataclasses import dataclass

from app.domain.shared.errors import DomainError


class UnknownGuide(DomainError):
    """No quick guide has this id."""

    code = "unknown_guide"

    def __init__(self, guide_id: str) -> None:
        super().__init__(f"Unknown guide '{guide_id}'", {"guideId": guide_id})


@dataclass(frozen=True)
class GuideResource:
    label: str
    number: str
    tel: str


@dataclass(frozen=True)
class GuideStep:
    title: str
    text: str


@dataclass(frozen=True)
class GuideSource:
    name: str
    url: str


@dataclass(frozen=True)
class GuideCommon:
    """Section titles and the footer shared by every guide."""

    footer: str
    call_now_title: str
    steps_title: str
    then_title: str
    dont_title: str
    resources_title: str


@dataclass(frozen=True)
class QuickGuide:
    """One guide; text may still hold `{recipient}`-style placeholders."""

    id: str
    title: str
    summary: str
    urgency: str
    call_now: tuple[str, ...]
    steps: tuple[GuideStep, ...]
    then: tuple[str, ...]
    dont: tuple[str, ...]
    resources: tuple[str, ...]
    sources: tuple[GuideSource, ...]


@dataclass(frozen=True)
class QuickGuideBook:
    common: GuideCommon
    resources: dict[str, GuideResource]
    guides: tuple[QuickGuide, ...]

    def get(self, guide_id: str) -> QuickGuide:
        for guide in self.guides:
            if guide.id == guide_id:
                return guide
        raise UnknownGuide(guide_id)


@dataclass(frozen=True)
class RenderedGuide:
    """A guide ready to show: placeholders filled, resource ids resolved."""

    id: str
    title: str
    summary: str
    urgency: str
    call_now_title: str
    call_now: tuple[str, ...]
    steps_title: str
    steps: tuple[GuideStep, ...]
    then_title: str
    then: tuple[str, ...]
    dont_title: str
    dont: tuple[str, ...]
    resources_title: str
    resources: tuple[GuideResource, ...]
    sources: tuple[GuideSource, ...]
    footer: str
