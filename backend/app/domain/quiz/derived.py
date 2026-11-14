"""Derived-tag conditions of quiz.json ("any row is 'missing' or 'not_sure'", "value 1-2")."""

import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.quiz.errors import QuizRuleError

_GRID = re.compile(r"^(any|all) rows? (?:is|are) (.+)$")
_SCALE = re.compile(r"^value (\d+)(?:-(\d+))?$")
_QUOTED = re.compile(r"'([^']+)'")


class DerivedTagRule(Protocol):
    @property
    def add(self) -> str: ...

    def matches(self, answer: Any) -> bool: ...


@dataclass(frozen=True)
class GridRowsRule:
    add: str
    quantifier: str  # "any" | "all"
    states: tuple[str, ...]

    def matches(self, answer: Any) -> bool:
        if not isinstance(answer, dict) or not answer:
            return False
        hits = [state in self.states for state in answer.values()]
        return any(hits) if self.quantifier == "any" else all(hits)


@dataclass(frozen=True)
class ScaleRangeRule:
    add: str
    low: int
    high: int

    def matches(self, answer: Any) -> bool:
        return isinstance(answer, int) and self.low <= answer <= self.high


def parse_derived_rule(condition: str, add: str) -> DerivedTagRule:
    """Read a condition string; an unreadable one fails loudly at startup, never silently."""
    text = condition.strip()
    grid = _GRID.match(text)
    if grid:
        states = tuple(_QUOTED.findall(grid.group(2)))
        if states:
            return GridRowsRule(add, grid.group(1), states)
    scale = _SCALE.match(text)
    if scale:
        low = int(scale.group(1))
        return ScaleRangeRule(add, low, int(scale.group(2) or low))
    raise QuizRuleError(f"Cannot read the derived-tag condition: {condition}", {"if": condition})
