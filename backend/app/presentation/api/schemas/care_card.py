"""Care card schemas. The public snapshot schema lists exactly the whitelisted fields."""

from datetime import date, datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.application.care_card.use_cases import CareCardView
from app.domain.care_card.entities import MAX_CARD_PHRASES, CardSnapshot
from app.domain.care_card.policies import CardStatus
from app.presentation.api.schemas.base import CamelModel
from app.presentation.api.schemas.profile import ContactOut


class CareCardRequest(CamelModel):
    """Unknown keys are rejected: only chosen saved-phrase ids can be sent."""

    model_config = ConfigDict(extra="forbid")

    phrase_ids: list[UUID] = Field(default_factory=list, max_length=MAX_CARD_PHRASES)


class HelplineOut(CamelModel):
    name: str
    phone: str
    description: str


class CardSnapshotOut(CamelModel):
    display_name: str
    enjoys: list[str]
    calms: list[str]
    avoid: list[str]
    rhythm: str
    contacts: list[ContactOut]
    helplines: list[HelplineOut]
    phrases: list[str]
    updated_on: date
    caregiver_first_name: str | None


def snapshot_out(s: CardSnapshot) -> CardSnapshotOut:
    return CardSnapshotOut(
        display_name=s.display_name,
        enjoys=list(s.enjoys),
        calms=list(s.calms),
        avoid=list(s.avoid),
        rhythm=s.rhythm,
        contacts=[ContactOut(name=c.name, phone=c.phone, role=c.role) for c in s.contacts],
        helplines=[
            HelplineOut(name=h.name, phone=h.phone, description=h.description) for h in s.helplines
        ],
        phrases=list(s.phrases),
        updated_on=s.updated_on,
        caregiver_first_name=s.caregiver_first_name,
    )


class AvailablePhrase(CamelModel):
    id: UUID
    text: str


class CareCardResponse(CamelModel):
    status: CardStatus
    link: str | None
    published: CardSnapshotOut | None
    preview: CardSnapshotOut
    chosen_phrase_ids: list[UUID]
    available_phrases: list[AvailablePhrase]
    new_phrase_count: int
    published_at: datetime | None
    updated_at: datetime | None
    last_opened_at: datetime | None
    revoked_at: datetime | None


def care_card_response(view: CareCardView, public_app_url: str) -> CareCardResponse:
    link = (
        None if view.link_token is None else f"{public_app_url.rstrip('/')}/card/{view.link_token}"
    )
    return CareCardResponse(
        status=view.status,
        link=link,
        published=None if view.published is None else snapshot_out(view.published),
        preview=snapshot_out(view.preview),
        chosen_phrase_ids=list(view.chosen_phrase_ids),
        available_phrases=[AvailablePhrase(id=p.id, text=p.text) for p in view.available_phrases],
        new_phrase_count=view.new_phrase_count,
        published_at=view.published_at,
        updated_at=view.updated_at,
        last_opened_at=view.last_opened_at,
        revoked_at=view.revoked_at,
    )
