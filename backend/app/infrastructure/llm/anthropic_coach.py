"""Single-call coach harness: one Anthropic request per caregiver reply.

Returns the model's RAW judgement (`CoachVerdict`); the domain recomputes the score. Every failure
(timeout, API error, refusal, invalid JSON, unknown flag) becomes `CoachUnavailable`. Nothing the
caregiver wrote and nothing the model answered is ever logged: only counts and outcomes.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Literal

from anthropic import AsyncAnthropic

from app.application.ports import CoachUnavailable
from app.application.roleplay.dto import CoachInput
from app.domain.roleplay.verdict import CoachVerdict
from app.infrastructure.llm.prompt import (
    INPUT_FORMAT_NOTE,
    PromptSpec,
    build_user_message,
)
from app.infrastructure.llm.schema import CoachResponse

logger = logging.getLogger(__name__)
# The SDK logs the full request options (the caregiver reply) at DEBUG: never allow that.
logging.getLogger("anthropic").setLevel(logging.WARNING)

HARNESS_ID: Final = "single_call"
MAX_TOKENS: Final = 1024
FALLBACK_BETA: Final = "server-side-fallback-2026-07-01"
# Models that accept the server-side refusal fallback (a list on others returns 400).
FALLBACK_MODELS: Final = frozenset({"claude-opus-5-5"})

Effort = Literal["low", "medium", "high", "xhigh", "max"]
_EFFORTS: Final = ("low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True)
class CallMetrics:
    """Per-call numbers for logs and the eval runner. Counts only, never text."""

    harness: str
    model: str
    effort: str
    prompt_version: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    outcome: str  # ok | no_api_key | timeout | api_error | refusal | max_tokens | invalid_output


class AnthropicCoach:
    """`Coach` port implementation over `messages.parse` (structured output)."""

    harness_id: Final = HARNESS_ID

    def __init__(
        self,
        client: AsyncAnthropic | None,
        *,
        prompt: PromptSpec,
        model: str,
        effort: str,
        timeout_seconds: float,
        thinking: dict[str, str] | None = None,
        metrics_sink: Callable[[CallMetrics], None] | None = None,
    ) -> None:
        if effort not in _EFFORTS:
            raise ValueError(f"COACH_EFFORT must be one of {_EFFORTS}, got {effort!r}")
        self._client = client
        self._prompt = prompt
        self._model = model
        self._effort: Effort = effort  # type: ignore[assignment]
        self._timeout = timeout_seconds
        self._thinking = thinking
        self._sink = metrics_sink
        # Static prefix: byte-stable, cache breakpoint on the last static block.
        self._system: list[dict[str, Any]] = [
            {"type": "text", "text": prompt.system},
            {
                "type": "text",
                "text": INPUT_FORMAT_NOTE,
                "cache_control": {"type": "ephemeral"},
            },
        ]

    async def turn(self, coach_input: CoachInput) -> CoachVerdict:
        started = time.perf_counter()
        usage = (0, 0, 0, 0)
        try:
            if self._client is None:
                raise _Failure("no_api_key")
            response = await asyncio.wait_for(self._call(coach_input), timeout=self._timeout)
            usage = _usage(response)
            if response.stop_reason == "refusal":
                raise _Failure("refusal")
            if response.stop_reason == "max_tokens":
                raise _Failure("max_tokens")
            parsed = response.parsed_output
            if not isinstance(parsed, CoachResponse):
                raise _Failure("invalid_output")
            verdict = parsed.to_verdict()
        except _Failure as failure:
            self._record(failure.outcome, started, usage)
            raise CoachUnavailable("The coach is unavailable.") from None
        except TimeoutError:
            self._record("timeout", started, usage)
            raise CoachUnavailable("The coach is unavailable.") from None
        except Exception as exc:
            self._record(_classify(exc), started, usage)
            raise CoachUnavailable("The coach is unavailable.") from None
        self._record("ok", started, usage)
        return verdict

    async def _call(self, coach_input: CoachInput) -> Any:
        assert self._client is not None  # noqa: S101 - narrowed by the caller
        client = self._client.with_options(max_retries=0, timeout=self._timeout)
        common: dict[str, Any] = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": self._system,
            "messages": [{"role": "user", "content": build_user_message(coach_input)}],
            "output_config": {"effort": self._effort},
            "output_format": CoachResponse,
        }
        if self._thinking is not None:
            common["thinking"] = self._thinking
        if self._model in FALLBACK_MODELS:
            return await client.beta.messages.parse(
                **common, fallbacks="default", betas=[FALLBACK_BETA]
            )
        return await client.messages.parse(**common)

    def _record(self, outcome: str, started: float, usage: tuple[int, int, int, int]) -> None:
        metrics = CallMetrics(
            harness=HARNESS_ID,
            model=self._model,
            effort=self._effort,
            prompt_version=self._prompt.version,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            input_tokens=usage[0],
            output_tokens=usage[1],
            cache_read_tokens=usage[2],
            cache_creation_tokens=usage[3],
            outcome=outcome,
        )
        logger.info(
            "coach_call harness=%s model=%s effort=%s prompt_version=%s latency_ms=%s "
            "input_tokens=%s output_tokens=%s cache_read_tokens=%s cache_creation_tokens=%s "
            "outcome=%s",
            metrics.harness,
            metrics.model,
            metrics.effort,
            metrics.prompt_version,
            metrics.latency_ms,
            metrics.input_tokens,
            metrics.output_tokens,
            metrics.cache_read_tokens,
            metrics.cache_creation_tokens,
            metrics.outcome,
            extra={"coach_metrics": metrics},
        )
        if self._sink is not None:
            self._sink(metrics)


class _Failure(Exception):
    def __init__(self, outcome: str) -> None:
        super().__init__(outcome)
        self.outcome = outcome


def _usage(response: Any) -> tuple[int, int, int, int]:
    u = response.usage
    return (
        int(u.input_tokens),
        int(u.output_tokens),
        int(u.cache_read_input_tokens or 0),
        int(u.cache_creation_input_tokens or 0),
    )


def _classify(exc: Exception) -> str:
    # Local import of the exception types keeps the module header small.
    from anthropic import APIError, APITimeoutError

    if isinstance(exc, APITimeoutError):
        return "timeout"
    if isinstance(exc, APIError):
        return "api_error"
    return "invalid_output"
