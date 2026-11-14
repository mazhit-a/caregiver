"""Coach verdict and the rules re-applied in code to any model output. Pure, stdlib only."""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.roleplay.errors import InvalidCoachOutput
from app.domain.shared.labels import RecipientLabels, render_text

MAX_SCORE_WHEN_ARGUED = 2


KNOWN_FLAGS = frozenset({"medical", "crisis", "off_topic", "too_short"})
KNOWN_MOODS = frozenset({"calmer", "same", "more_upset"})


class OutcomeKind(StrEnum):
    COACHED = "coached"
    CRISIS = "crisis"


@dataclass(frozen=True)
class Goals:
    notice: bool
    reassure: bool
    offer: bool

    @property
    def count(self) -> int:
        return int(self.notice) + int(self.reassure) + int(self.offer)


NO_GOALS = Goals(False, False, False)


@dataclass(frozen=True)
class CoachVerdict:
    """What the model claims. Its own score is never read: `apply_rules` recomputes it."""

    goals: Goals
    argued: bool
    flags: tuple[str, ...]
    tip: str
    better_phrase: str
    parent_reaction: str
    parent_mood: str


def validate_verdict(verdict: CoachVerdict) -> CoachVerdict:
    """Strict check of a model output: known flags and mood. Raises `InvalidCoachOutput`."""
    unknown = [f for f in verdict.flags if f not in KNOWN_FLAGS]
    if unknown or verdict.parent_mood not in KNOWN_MOODS:
        raise InvalidCoachOutput("The coach output is not valid.")
    return verdict


@dataclass(frozen=True)
class CoachTips:
    """Fixed tip templates from content (`{label}` is the parent label)."""

    medical: str
    off_topic: str
    too_short: str


@dataclass(frozen=True)
class CoachOutcome:
    kind: OutcomeKind
    score: int
    goals: Goals
    argued: bool
    flags: tuple[str, ...]
    tip: str
    better_phrase: str
    parent_reaction: str
    parent_mood: str


def apply_rules(
    verdict: CoachVerdict,
    tips: CoachTips,
    labels: RecipientLabels,
    label: str,
) -> CoachOutcome:
    """Flag precedence: crisis, medical, off_topic, too_short, then plain scoring."""
    flags = verdict.flags
    extra = {"label": label}

    def fixed(kind: OutcomeKind, tip: str, *, keep_reaction: bool) -> CoachOutcome:
        return CoachOutcome(
            kind=kind,
            score=0,
            goals=NO_GOALS,
            argued=False,
            flags=flags,
            tip=tip,
            better_phrase=verdict.better_phrase if kind is not OutcomeKind.CRISIS else "",
            parent_reaction=verdict.parent_reaction if keep_reaction else "",
            parent_mood=verdict.parent_mood,
        )

    if "crisis" in flags:
        return fixed(OutcomeKind.CRISIS, "", keep_reaction=False)
    if "medical" in flags:
        tip = render_text(tips.medical, labels, extra)
        return fixed(OutcomeKind.COACHED, tip, keep_reaction=False)
    if "off_topic" in flags:
        tip = render_text(tips.off_topic, labels, extra)
        return fixed(OutcomeKind.COACHED, tip, keep_reaction=True)
    if "too_short" in flags:
        tip = render_text(tips.too_short, labels, extra)
        return fixed(OutcomeKind.COACHED, tip, keep_reaction=True)

    score = verdict.goals.count
    if verdict.argued:
        score = min(score, MAX_SCORE_WHEN_ARGUED)
    return CoachOutcome(
        kind=OutcomeKind.COACHED,
        score=score,
        goals=verdict.goals,
        argued=verdict.argued,
        flags=flags,
        tip=verdict.tip,
        better_phrase=verdict.better_phrase,
        parent_reaction=verdict.parent_reaction,
        parent_mood=verdict.parent_mood,
    )
