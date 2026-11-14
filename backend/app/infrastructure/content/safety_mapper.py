"""Maps the safety-terms file to the domain types of the role-play and safety checks."""

from app.domain.roleplay.verdict import CoachTips
from app.domain.safety.check import SafetyTerms
from app.infrastructure.content.schemas import SafetyTermsFile


def to_safety_terms(file: SafetyTermsFile) -> SafetyTerms:
    return SafetyTerms(
        crisis=tuple(file.crisis),
        emergency=tuple(file.emergency),
        excluded_phrases=tuple(file.matching.excluded_phrases),
    )


def to_coach_tips(file: SafetyTermsFile) -> CoachTips:
    tips = file.coach_tips
    return CoachTips(medical=tips.medical, off_topic=tips.off_topic, too_short=tips.too_short)
