"""Model-based judge (ai.md section 4): a stronger model grades the coach's written outputs
against a three-item rubric, 1-5 plus a one-line reason each.

Nothing here calls the network on its own: the client is the `ModelClient` seam (the real SDK in a
manual run, a fake in tests). Request shape follows the coach adapter and the current API facts:
no temperature, no prefill, no forced tool_choice, `effort` set explicitly, `stop_reason` checked,
output validated strictly. The reply and the coach's output are DATA inside XML tags.
A judge may only feed selection after a passing calibration (see `evals/calibrate.py`).
"""

import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal
from xml.sax.saxutils import escape

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.infrastructure.llm.anthropic_coach import FALLBACK_BETA, FALLBACK_MODELS
from evals.client import ModelClient

JUDGE_PROMPT_DIR: Final = Path(__file__).resolve().parents[1] / "prompts"
JUDGE_PROMPT_VERSION: Final = "v1"
JUDGE_MAX_TOKENS: Final = 1024
JUDGE_TIMEOUT_SECONDS: Final = 60.0
JUDGE_EFFORT: Final = "medium"
EFFORTS: Final = ("low", "medium", "high", "xhigh", "max")
MAX_REASON_CHARS: Final = 240

BETTER_PHRASE: Final = "better_phrase"
TIP: Final = "tip"
PARENT_REACTION: Final = "parent_reaction"
RUBRIC_ITEMS: Final = (BETTER_PHRASE, TIP, PARENT_REACTION)


class JudgePromptError(Exception):
    """The judge prompt file is missing or empty."""


class JudgeUnavailable(Exception):
    """One judge call failed (no client, timeout, API error, refusal, truncation, bad output).
    `outcome` is a short code; no text from the item is ever put in it."""

    def __init__(self, outcome: str) -> None:
        super().__init__(outcome)
        self.outcome = outcome


# ------------------------------------------------------------------ output schema


class _Strict(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class RubricScore(_Strict):
    score: int = Field(ge=1, le=5)
    reason: str

    @field_validator("reason")
    @classmethod
    def _one_line(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("reason must not be empty")
        if "\n" in text or "\r" in text:
            raise ValueError("reason must be one line")
        if len(text) > MAX_REASON_CHARS:
            raise ValueError(f"reason must be at most {MAX_REASON_CHARS} characters")
        return text


class JudgeResponse(_Strict):
    """The OUTPUT contract of `judge.v1.md`: all three items, strict."""

    better_phrase: RubricScore
    tip: RubricScore
    parent_reaction: RubricScore

    def scores(self) -> dict[str, int]:
        return {
            BETTER_PHRASE: self.better_phrase.score,
            TIP: self.tip.score,
            PARENT_REACTION: self.parent_reaction.score,
        }


def to_unit(score: int) -> float:
    """1-5 -> 0-1 (1 -> 0.0, 3 -> 0.5, 5 -> 1.0), the scale `ConfigMetrics.quality` expects."""
    if not 1 <= score <= 5:
        raise ValueError("judge score must be 1-5")
    return (score - 1) / 4


# ------------------------------------------------------------------ prompt and input


@dataclass(frozen=True)
class JudgePrompt:
    version: str
    system: str
    sha256: str


def load_judge_prompt(
    version: str = JUDGE_PROMPT_VERSION, directory: Path = JUDGE_PROMPT_DIR
) -> JudgePrompt:
    path = directory / f"judge.{version}.md"
    if not path.is_file():
        raise JudgePromptError(f"Judge prompt not found: {path}")
    raw = path.read_bytes()
    text = raw.decode("utf-8").strip()
    if not text:
        raise JudgePromptError(f"Judge prompt is empty: {path}")
    return JudgePrompt(version, text, hashlib.sha256(raw).hexdigest())


@dataclass(frozen=True)
class JudgeItem:
    """One exchange to grade: the scenario, the caregiver reply and the coach's final output."""

    label: str
    parent_line: str
    parent_mood: str
    caregiver_reply: str
    tip: str
    better_phrase: str
    parent_reaction: str
    coach_parent_mood: str
    coach_score: int
    previous_turns: tuple[tuple[str, str], ...] = ()  # (parent, caregiver)


def build_judge_message(item: JudgeItem) -> str:
    def tag(name: str, value: str) -> str:
        return f"<{name}>{escape(value)}</{name}>"

    previous = "\n".join(
        f"<turn>{tag('parent', p)}{tag('caregiver', c)}</turn>" for p, c in item.previous_turns
    )
    return (
        "<scenario>\n"
        f"{tag('label', item.label)}\n{tag('parent_line', item.parent_line)}\n"
        f"{tag('parent_mood', item.parent_mood)}\n</scenario>\n"
        f"<previous_turns>\n{previous}\n</previous_turns>\n"
        f"{tag('caregiver_reply', item.caregiver_reply)}\n"
        "<coach_output>\n"
        f"<score>{item.coach_score}</score>\n{tag('better_phrase', item.better_phrase)}\n"
        f"{tag('tip', item.tip)}\n{tag('parent_reaction', item.parent_reaction)}\n"
        f"{tag('parent_mood', item.coach_parent_mood)}\n</coach_output>"
    )


# ------------------------------------------------------------------ the judge


@dataclass(frozen=True)
class JudgeUsage:
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int


@dataclass(frozen=True)
class JudgeScores:
    scores: dict[str, int]  # rubric item -> 1-5
    reasons: dict[str, str]
    usage: JudgeUsage

    def units(self) -> dict[str, float]:
        return {k: to_unit(v) for k, v in self.scores.items()}


class Judge:
    def __init__(
        self,
        client: ModelClient | None,
        *,
        prompt: JudgePrompt,
        model: str,
        effort: str = JUDGE_EFFORT,
        timeout_seconds: float = JUDGE_TIMEOUT_SECONDS,
    ) -> None:
        if effort not in EFFORTS:
            raise ValueError(f"judge effort must be one of {EFFORTS}, got {effort!r}")
        self._client = client
        self.prompt = prompt
        self.model = model
        self.effort: Literal["low", "medium", "high", "xhigh", "max"] = effort  # type: ignore[assignment]
        self._timeout = timeout_seconds
        self._system: list[dict[str, Any]] = [
            {"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}
        ]

    async def judge(self, item: JudgeItem) -> JudgeScores:
        """Raises `JudgeUnavailable` on any failure; never returns a partial result."""
        if self._client is None:
            raise JudgeUnavailable("no_api_key")
        try:
            response = await asyncio.wait_for(self._call(item), timeout=self._timeout)
        except TimeoutError:
            raise JudgeUnavailable("timeout") from None
        except Exception:
            raise JudgeUnavailable("api_error") from None
        stop = getattr(response, "stop_reason", None)
        if stop == "refusal":
            raise JudgeUnavailable("refusal")
        if stop == "max_tokens":
            raise JudgeUnavailable("max_tokens")
        if stop != "end_turn":
            raise JudgeUnavailable("unexpected_stop")
        parsed = getattr(response, "parsed_output", None)
        if not isinstance(parsed, JudgeResponse):
            raise JudgeUnavailable("invalid_output")
        try:
            strict = JudgeResponse.model_validate(parsed.model_dump(by_alias=True))
        except ValueError:
            raise JudgeUnavailable("invalid_output") from None
        u = response.usage
        usage = JudgeUsage(
            self.model,
            int(u.input_tokens),
            int(u.output_tokens),
            int(u.cache_read_input_tokens or 0),
            int(u.cache_creation_input_tokens or 0),
        )
        return JudgeScores(
            scores=strict.scores(),
            reasons={
                BETTER_PHRASE: strict.better_phrase.reason,
                TIP: strict.tip.reason,
                PARENT_REACTION: strict.parent_reaction.reason,
            },
            usage=usage,
        )

    async def _call(self, item: JudgeItem) -> Any:
        assert self._client is not None  # noqa: S101 - narrowed by the caller
        client = self._client.with_options(max_retries=0, timeout=self._timeout)
        common: dict[str, Any] = {
            "model": self.model,
            "max_tokens": JUDGE_MAX_TOKENS,
            "system": self._system,
            "messages": [{"role": "user", "content": build_judge_message(item)}],
            "output_config": {"effort": self.effort},
            "output_format": JudgeResponse,
        }
        if self.model in FALLBACK_MODELS:
            return await client.beta.messages.parse(
                **common, fallbacks="default", betas=[FALLBACK_BETA]
            )
        return await client.messages.parse(**common)
