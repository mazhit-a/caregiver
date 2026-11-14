"""Role-play run: mode, scores and goals only. Reply text is never part of the entity."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.roleplay.errors import InvalidReply
from app.domain.roleplay.verdict import Goals

MAX_REPLY_CHARS = 500
PERFECT_SCORE = 3


class RunMode(StrEnum):
    AI = "ai"
    FALLBACK = "fallback"


def validate_reply(text: str) -> str:
    """Return the trimmed reply; reject empty or over 500 characters."""
    if len(text) > MAX_REPLY_CHARS:
        raise InvalidReply("Reply is too long", {"max": MAX_REPLY_CHARS})
    trimmed = text.strip()
    if not trimmed:
        raise InvalidReply("Reply is empty", {"min": 1})
    return trimmed


@dataclass(frozen=True)
class RunSummary:
    first_score: int | None
    last_score: int | None
    improved: bool
    notice_turns: int
    reassure_turns: int
    offer_turns: int


@dataclass
class RoleplayRun:
    rounds_total: int
    mode: RunMode = RunMode.AI
    turn_scores: list[int] = field(default_factory=list)
    goals_hit: list[Goals] = field(default_factory=list)

    def switch_to_fallback(self) -> None:
        """One-way: there is no way back to `ai` for the rest of the run."""
        self.mode = RunMode.FALLBACK

    def record_turn(self, score: int, goals: Goals) -> None:
        self.turn_scores.append(score)
        self.goals_hit.append(goals)

    def summary(self) -> RunSummary:
        first = self.turn_scores[0] if self.turn_scores else None
        last = self.turn_scores[-1] if self.turn_scores else None
        return RunSummary(
            first_score=first,
            last_score=last,
            improved=first is not None and last is not None and last > first,
            notice_turns=sum(g.notice for g in self.goals_hit),
            reassure_turns=sum(g.reassure for g in self.goals_hit),
            offer_turns=sum(g.offer for g in self.goals_hit),
        )


@dataclass(frozen=True)
class TurnPhrases:
    """In-memory only, per request: the reply, its score and the coach's better phrase."""

    score: int
    reply: str
    better_phrase: str


def best_phrase(turns: Sequence[TurnPhrases]) -> str | None:
    """The first reply that scored 3, else the last turn's better phrase."""
    for turn in turns:
        if turn.score == PERFECT_SCORE:
            return turn.reply
    return turns[-1].better_phrase if turns else None
