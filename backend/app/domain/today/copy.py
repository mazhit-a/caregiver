"""The wording of the Today screen (content/funnel-copy.json `today`), placeholders unfilled."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoControlCopy:
    id: str
    label: str


@dataclass(frozen=True)
class TodayCopy:
    title: str
    rest_message: str
    all_built_done: str
    next_unlock: str
    care_card_nudge_one: str
    care_card_nudge_many: str
    weekly_rhythm: str
    readiness: str
    renews_on: str
    renewed: str
    ends_on: str
    welcome_back_title: str
    welcome_back_body: str
    visit_sheet_link: str
    demo_label: str
    demo_controls: tuple[DemoControlCopy, ...]
    welcome_back_after_days: int
    renewed_notice_days: int
