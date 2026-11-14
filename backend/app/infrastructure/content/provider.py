"""ContentProvider adapter over the loaded content bundle."""

from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.billing.exit_copy import GentleExitCopy, GentleExitResourceCopy
from app.domain.billing.pricing import Pricing, PricingPlan
from app.domain.plan.entities import PhraseSheetText, PhraseText, PlanRules
from app.domain.quiz.definition import QuizDefinition
from app.domain.roleplay.verdict import CoachTips
from app.domain.safety.check import SafetyTerms
from app.domain.safety.resources import CrisisResource
from app.domain.shared.errors import DomainError
from app.domain.shared.labels import (
    RecipientLabels,
    lesson_labels,
    render_text,
    with_display_name,
)
from app.domain.today.copy import DemoControlCopy, TodayCopy
from app.domain.visit_sheet.entities import BankQuestion, VisitQuestionBank
from app.infrastructure.content.loader import ContentBundle, load_content
from app.infrastructure.content.plan_rules_mapper import to_plan_rules
from app.infrastructure.content.quiz_mapper import to_quiz_definition
from app.infrastructure.content.safety_mapper import to_coach_tips, to_safety_terms
from app.infrastructure.content.schemas import LessonFile

_AUTHORING_KEYS = frozenset({"notes"})


class UnknownContentReference(DomainError):
    """A lesson, recipient key or variant that the content does not define."""

    code = "unknown_content_reference"


class JsonContentProvider:
    """Implements the `ContentProvider` port from validated JSON content."""

    def __init__(self, bundle: ContentBundle) -> None:
        self._bundle = bundle
        self._quiz_definition = to_quiz_definition(bundle.quiz)
        self._plan_rules = to_plan_rules(bundle.plan_rules, bundle.phrases)
        self._labels = {
            key: RecipientLabels.from_mapping(model.model_dump(by_alias=True))
            for key, model in bundle.quiz.recipient_labels.items()
        }

    @classmethod
    def from_directory(cls, content_dir: Path) -> "JsonContentProvider":
        return cls(load_content(content_dir))

    @property
    def content_version(self) -> str:
        return self._bundle.content_version

    def recipient_keys(self) -> list[str]:
        return list(self._labels)

    def recipient_labels(self, key: str) -> RecipientLabels:
        if key not in self._labels:
            raise UnknownContentReference(f"Unknown recipient key '{key}'", {"key": key})
        return self._labels[key]

    def lesson_recipient_labels(self, key: str, display_name: str | None = None) -> RecipientLabels:
        self.recipient_labels(key)  # validates the key
        return with_display_name(lesson_labels(key, self._labels), display_name)

    def crisis_resources(self) -> list[CrisisResource]:
        return [
            CrisisResource(id=r.id, name=r.name, phone=r.phone, description=r.description)
            for r in self._bundle.crisis_resources.resources
        ]

    def visit_questions(self) -> VisitQuestionBank:
        file = self._bundle.visit_questions
        return VisitQuestionBank(
            file.footer, tuple(BankQuestion(q.id, q.text) for q in file.questions)
        )

    def safety_terms(self) -> SafetyTerms:
        return to_safety_terms(self._bundle.safety_terms)

    def coach_tips(self) -> CoachTips:
        return to_coach_tips(self._bundle.safety_terms)

    def today_copy(self) -> TodayCopy:
        t = self._bundle.funnel_copy.today
        return TodayCopy(
            title=t.title,
            rest_message=t.rest_message,
            all_built_done=t.all_built_done,
            next_unlock=t.next_unlock,
            care_card_nudge_one=t.care_card_nudge_one,
            care_card_nudge_many=t.care_card_nudge_many,
            weekly_rhythm=t.weekly_rhythm,
            readiness=t.readiness,
            renews_on=t.subscription.renews_on,
            renewed=t.subscription.renewed,
            ends_on=t.subscription.ends_on,
            welcome_back_title=t.welcome_back.title,
            welcome_back_body=t.welcome_back.body,
            visit_sheet_link=t.visit_sheet_link,
            demo_label=t.demo.label,
            demo_controls=tuple(DemoControlCopy(c.id, c.label) for c in t.demo.controls),
            welcome_back_after_days=t.welcome_back_after_days,
            renewed_notice_days=t.renewed_notice_days,
        )

    def gentle_exit_copy(self) -> GentleExitCopy:
        g = self._bundle.funnel_copy.gentle_exit
        return GentleExitCopy(
            title=g.title,
            condolence=g.condolence,
            resources_intro=g.resources_intro,
            resources=tuple(
                GentleExitResourceCopy(r.id, r.name, r.description, r.phone, r.url)
                for r in g.resources
            ),
            clear_data_confirmation=g.clear_data_confirmation,
        )

    def crisis_resources_need_verification(self) -> bool:
        return self._bundle.crisis_resources.verify_before_launch

    def pricing(self) -> Pricing:
        file = self._bundle.pricing
        return Pricing(
            currency=file.currency,
            default_plan_id=file.default_plan_id,
            plans=tuple(
                PricingPlan(
                    id=p.id,
                    label=p.label,
                    intro_price=Decimal(str(p.intro_price)),
                    intro_days=p.intro_days,
                    intro_period_text=p.intro_period_text,
                    renew_price=Decimal(str(p.renew_price)),
                    renew_days=p.renew_days,
                    renew_period_text=p.renew_period_text,
                    stripe_intro_price_id=p.stripe_intro_price_id,
                    stripe_renew_price_id=p.stripe_renew_price_id,
                    stripe_intro_coupon_id=p.stripe_intro_coupon_id,
                )
                for p in file.plans
            ),
        )

    def quiz_definition(self) -> QuizDefinition:
        return self._quiz_definition

    def plan_rules(self) -> PlanRules:
        return self._plan_rules

    def phrase_sheet(self) -> PhraseSheetText:
        sheet = self._bundle.phrases.sheet
        return PhraseSheetText(sheet.title, sheet.intro, sheet.footer)

    def phrases(self) -> list[PhraseText]:
        return [PhraseText(p.id, p.text, p.when) for p in self._bundle.phrases.phrases]

    def lesson_ids(self) -> list[str]:
        return sorted(self._bundle.lessons)

    def lesson_variants(self, lesson_id: str) -> list[str]:
        return self._lesson(lesson_id).variant_ids()

    def render_lesson(
        self,
        lesson_id: str,
        recipient_key: str,
        variant: str | None = None,
        runtime_values: Mapping[str, str] | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Lesson as camelCase JSON data with every placeholder filled (authoring notes dropped).

        Runtime placeholders ({savedPhrase}, {firstScore}, ...) must be supplied by the caller;
        a placeholder without a value raises. Variant maps are left for the lesson use case.
        """
        lesson = self._lesson(lesson_id)
        variants = lesson.variant_ids()
        if variant is not None and variant not in variants:
            raise UnknownContentReference(
                f"Lesson '{lesson_id}' has no variant '{variant}'",
                {"lesson": lesson_id, "variant": variant},
            )
        labels = self.lesson_recipient_labels(recipient_key, display_name)
        data = lesson.model_dump(by_alias=True, mode="json", exclude_none=True)
        return {
            key: _render_tree(value, labels, runtime_values)
            for key, value in data.items()
            if key not in _AUTHORING_KEYS
        }

    def _lesson(self, lesson_id: str) -> LessonFile:
        if lesson_id not in self._bundle.lessons:
            raise UnknownContentReference(f"Unknown lesson '{lesson_id}'", {"lesson": lesson_id})
        return self._bundle.lessons[lesson_id]


def _render_tree(node: Any, labels: RecipientLabels, extra: Mapping[str, str] | None) -> Any:
    if isinstance(node, str):
        return render_text(node, labels, extra)
    if isinstance(node, list):
        return [_render_tree(item, labels, extra) for item in node]
    if isinstance(node, dict):
        return {key: _render_tree(value, labels, extra) for key, value in node.items()}
    return node
