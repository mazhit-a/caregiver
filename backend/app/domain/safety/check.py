"""Local safety check: classify a caregiver reply before any model call. Pure, stdlib only."""

import re
from dataclasses import dataclass
from enum import StrEnum


class SafetyKind(StrEnum):
    CRISIS = "crisis"
    EMERGENCY = "emergency"
    NONE = "none"


@dataclass(frozen=True)
class SafetyTerms:
    """Terms from content/safety-terms.json. Matching is lowercase, whole word / whole phrase."""

    crisis: tuple[str, ...]
    emergency: tuple[str, ...]
    excluded_phrases: tuple[str, ...] = ()


def _normalise(text: str) -> str:
    text = text.replace("\N{RIGHT SINGLE QUOTATION MARK}", "'").replace(
        "\N{LEFT SINGLE QUOTATION MARK}", "'"
    )
    return re.sub(r"\s+", " ", text.lower()).strip()


def _contains(haystack: str, term: str) -> bool:
    needle = re.escape(_normalise(term)).replace("\\ ", " ")
    return re.search(rf"(?<![\w']){needle}(?![\w])", haystack) is not None


def _mask_excluded(text: str, excluded: tuple[str, ...]) -> str:
    for phrase in excluded:
        needle = re.escape(_normalise(phrase)).replace("\\ ", " ")
        text = re.sub(rf"(?<![\w']){needle}(?![\w])", " ", text)
    return text


class SafetyCheck:
    @staticmethod
    def classify(text: str, terms: SafetyTerms) -> SafetyKind:
        """Crisis wins over emergency; excluded phrases are removed before matching."""
        haystack = _mask_excluded(_normalise(text), terms.excluded_phrases)
        if any(_contains(haystack, term) for term in terms.crisis):
            return SafetyKind.CRISIS
        if any(_contains(haystack, term) for term in terms.emergency):
            return SafetyKind.EMERGENCY
        return SafetyKind.NONE
