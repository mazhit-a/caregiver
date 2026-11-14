"""Fakes and fixtures for the judge tests: no network, no key."""

import json
import re
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from evals.graders.judge import JudgeResponse
from evals.labels import HumanLabel, parse_labels

HUMAN_PATTERN = [1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 5, 3]


def judge_response(better: int, tip: int, reaction: int) -> JudgeResponse:
    return JudgeResponse.model_validate(
        {
            "betterPhrase": {"score": better, "reason": "ok"},
            "tip": {"score": tip, "reason": "ok"},
            "parentReaction": {"score": reaction, "reason": "ok"},
        }
    )


def label_row(i: int, human: tuple[int, int, int]) -> dict[str, Any]:
    return {
        "id": f"h{i:02d}",
        "labeler": "tester",
        "label": "Mom",
        "parentLine": f"line-{i:02d}",
        "parentMood": "worried",
        "previousTurns": [],
        "caregiverReply": f"reply {i}",
        "coachOutput": {
            "score": 2,
            "tip": f"tip {i}",
            "betterPhrase": f"better {i}",
            "parentReaction": f"reaction {i}",
            "parentMood": "calmer",
        },
        "human": {"betterPhrase": human[0], "tip": human[1], "parentReaction": human[2]},
    }


def fixture_labels(n: int = 20) -> list[HumanLabel]:
    rows = [
        label_row(
            i, (HUMAN_PATTERN[i % 20], HUMAN_PATTERN[(i + 7) % 20], HUMAN_PATTERN[(i + 13) % 20])
        )
        for i in range(n)
    ]
    return parse_labels("\n".join(json.dumps(r) for r in rows))


def miss(score: int) -> int:
    """A score two away from `score`: a disagreement beyond the +-1 tolerance."""
    return score + 2 if score <= 3 else score - 2


def scripted_scores(
    labels: list[HumanLabel], misses: dict[str, int], off_by_one: dict[str, int] | None = None
) -> dict[str, JudgeResponse]:
    """Judge answers per parent line: equal to the human score except for the first `misses[item]`
    rows of each item (two away) and the first `off_by_one[item]` remaining rows (one away)."""
    off_by_one = off_by_one or {}
    out: dict[str, JudgeResponse] = {}
    items = ("betterPhrase", "tip", "parentReaction")
    for idx, label in enumerate(labels):
        human = label.human_scores()
        values: list[int] = []
        for name, key in zip(items, ("better_phrase", "tip", "parent_reaction"), strict=True):
            h = human[key]
            if idx < misses.get(key, 0):
                values.append(miss(h))
            elif idx < misses.get(key, 0) + off_by_one.get(key, 0):
                values.append(h + 1 if h < 5 else h - 1)
            else:
                values.append(h)
            del name
        out[label.parent_line] = judge_response(*values)
    return out


class FakeJudgeClient:
    """Shaped like the SDK for `messages.parse`; answers per `<parent_line>` in the request."""

    def __init__(
        self,
        answer: Callable[[str], JudgeResponse | None] | JudgeResponse | None = None,
        *,
        stop_reason: str = "end_turn",
        raises: Exception | None = None,
    ) -> None:
        self.answer = answer
        self.stop_reason = stop_reason
        self.raises = raises
        self.requests: list[dict[str, Any]] = []
        self.messages = SimpleNamespace(parse=self._parse)
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def with_options(self, *, max_retries: int, timeout: float) -> "FakeJudgeClient":
        assert max_retries == 0
        return self

    async def _parse(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        if self.raises is not None:
            raise self.raises
        content: str = kwargs["messages"][0]["content"]
        found = re.search(r"<parent_line>(.*?)</parent_line>", content)
        line = found.group(1) if found else ""
        parsed = self.answer(line) if callable(self.answer) else self.answer
        usage = SimpleNamespace(
            input_tokens=300,
            output_tokens=60,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        return SimpleNamespace(stop_reason=self.stop_reason, parsed_output=parsed, usage=usage)
