from app.domain.guides.entities import RenderedGuide
from app.presentation.api.schemas.base import CamelModel


class GuideSummaryOut(CamelModel):
    id: str
    title: str
    summary: str
    urgency: str


class GuideListResponse(CamelModel):
    guides: list[GuideSummaryOut]


class GuideStepOut(CamelModel):
    title: str
    text: str


class GuideResourceOut(CamelModel):
    label: str
    number: str
    tel: str


class GuideSourceOut(CamelModel):
    name: str
    url: str


class GuideResponse(CamelModel):
    id: str
    title: str
    summary: str
    urgency: str
    call_now_title: str
    call_now: list[str]
    steps_title: str
    steps: list[GuideStepOut]
    then_title: str
    then: list[str]
    dont_title: str
    dont: list[str]
    resources_title: str
    resources: list[GuideResourceOut]
    sources: list[GuideSourceOut]
    footer: str

    @classmethod
    def from_rendered(cls, g: RenderedGuide) -> "GuideResponse":
        return cls(
            id=g.id,
            title=g.title,
            summary=g.summary,
            urgency=g.urgency,
            call_now_title=g.call_now_title,
            call_now=list(g.call_now),
            steps_title=g.steps_title,
            steps=[GuideStepOut(title=s.title, text=s.text) for s in g.steps],
            then_title=g.then_title,
            then=list(g.then),
            dont_title=g.dont_title,
            dont=list(g.dont),
            resources_title=g.resources_title,
            resources=[
                GuideResourceOut(label=r.label, number=r.number, tel=r.tel) for r in g.resources
            ],
            sources=[GuideSourceOut(name=x.name, url=x.url) for x in g.sources],
            footer=g.footer,
        )
