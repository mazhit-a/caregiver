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
from pydantic import BaseModel

from app.application.ports import CoachUnavailable
from app.application.roleplay.dto import CoachInput
from app.domain.roleplay.verdict import CoachVerdict
from app.infrastructure.llm.prompt import PromptSpec, build_user_message
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
EFFORTS: Final = ("low", "medium", "high", "xhigh", "max")


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
    role: str = "single"  # single | coach | parent (parallel_split reports one record per call)


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
        if effort not in EFFORTS:
            raise ValueError(f"COACH_EFFORT must be one of {EFFORTS}, got {effort!r}")
        self._client = client
        self._prompt = prompt
        self._model = model
        self._effort: Effort = effort  # type: ignore[assignment]
        self._timeout = timeout_seconds
        self._thinking = thinking
        self._sink = metrics_sink
        self._system = build_system(prompt.system, prompt.input_format_note)

    async def turn(self, coach_input: CoachInput) -> CoachVerdict:
        started = time.perf_counter()
        usage = (0, 0, 0, 0)
        try:
            if self._client is None:
                raise CallFailure("no_api_key")
            response = await asyncio.wait_for(self._call(coach_input), timeout=self._timeout)
            usage = usage_of(response)
            parsed = parsed_output(response, CoachResponse)
            verdict = parsed.to_verdict()
        except CallFailure as failure:
            self._record(failure.outcome, started, usage)
            raise CoachUnavailable("The coach is unavailable.") from None
        except TimeoutError:
            self._record("timeout", started, usage)
            raise CoachUnavailable("The coach is unavailable.") from None
        except Exception as exc:
            self._record(classify_error(exc), started, usage)
            raise CoachUnavailable("The coach is unavailable.") from None
        self._record("ok", started, usage)
        return verdict

    async def _call(self, coach_input: CoachInput) -> Any:
        assert self._client is not None  # noqa: S101 - narrowed by the caller
        return await send_structured(
            self._client,
            model=self._model,
            effort=self._effort,
            thinking=self._thinking,
            system=self._system,
            user=build_user_message(coach_input),
            schema=CoachResponse,
            sdk_timeout=self._timeout,
        )

    def _record(self, outcome: str, started: float, usage: tuple[int, int, int, int]) -> None:
        emit_metrics(
            CallMetrics(
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
            ),
            self._sink,
        )


class CallFailure(Exception):
    """A call that must become `CoachUnavailable`; `outcome` is the metrics outcome."""

    def __init__(self, outcome: str) -> None:
        super().__init__(outcome)
        self.outcome = outcome


def build_system(text: str, note: str | None = None) -> list[dict[str, Any]]:
    """Static prefix: byte-stable, cache breakpoint on the last static block."""
    if note is None:
        return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
    return [
        {"type": "text", "text": text},
        {"type": "text", "text": note, "cache_control": {"type": "ephemeral"}},
    ]


async def send_structured(
    client: AsyncAnthropic,
    *,
    model: str,
    effort: str,
    thinking: dict[str, str] | None,
    system: list[dict[str, Any]],
    user: str,
    schema: type[BaseModel],
    sdk_timeout: float,
) -> Any:
    """One structured-output request: no temperature, prefill, tools or retries."""
    scoped = client.with_options(max_retries=0, timeout=sdk_timeout)
    common: dict[str, Any] = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"effort": effort},
        "output_format": schema,
    }
    if thinking is not None:
        common["thinking"] = thinking
    if model in FALLBACK_MODELS:
        return await scoped.beta.messages.parse(
            **common, fallbacks="default", betas=[FALLBACK_BETA]
        )
    return await scoped.messages.parse(**common)


def parsed_output[T: BaseModel](response: Any, schema: type[T]) -> T:
    """The parsed model output, or `CallFailure` for a refusal, truncation or wrong shape."""
    if response.stop_reason == "refusal":
        raise CallFailure("refusal")
    if response.stop_reason == "max_tokens":
        raise CallFailure("max_tokens")
    parsed = response.parsed_output
    if not isinstance(parsed, schema):
        raise CallFailure("invalid_output")
    return parsed


def emit_metrics(metrics: CallMetrics, sink: Callable[[CallMetrics], None] | None) -> None:
    """Log one call (counts and outcome only, never text) and hand it to the sink."""
    logger.info(
        "coach_call harness=%s role=%s model=%s effort=%s prompt_version=%s latency_ms=%s "
        "input_tokens=%s output_tokens=%s cache_read_tokens=%s cache_creation_tokens=%s "
        "outcome=%s",
        metrics.harness,
        metrics.role,
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
    if sink is not None:
        sink(metrics)


def usage_of(response: Any) -> tuple[int, int, int, int]:
    u = response.usage
    return (
        int(u.input_tokens),
        int(u.output_tokens),
        int(u.cache_read_input_tokens or 0),
        int(u.cache_creation_input_tokens or 0),
    )


def classify_error(exc: Exception) -> str:
    from anthropic import APIError, APITimeoutError

    if isinstance(exc, APITimeoutError):
        return "timeout"
    if isinstance(exc, APIError):
        return "api_error"
    return "invalid_output"
