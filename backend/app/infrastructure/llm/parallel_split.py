"""Parallel-split coach harness: the COACH call and the PARENT call run concurrently.

Both calls start together and share ONE deadline (`LLM_TIMEOUT_SECONDS` from the start of the
turn). The coach call returns goals, argued, score, tip, betterPhrase and flags; the parent call
returns parentReaction and parentMood and may use a cheaper model. The results are merged into
one `CoachVerdict` with the same contract as the single call. If either call fails there is no
partial verdict: `CoachUnavailable`, and the still-running call is cancelled. One `CallMetrics`
per call (role "coach" / "parent"), counts only, never text.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any, Final

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.application.ports import CoachUnavailable
from app.application.roleplay.dto import CoachInput
from app.domain.roleplay.verdict import CoachVerdict
from app.infrastructure.llm.anthropic_coach import (
    EFFORTS,
    CallFailure,
    CallMetrics,
    build_system,
    classify_error,
    emit_metrics,
    parsed_output,
    send_structured,
    usage_of,
)
from app.infrastructure.llm.prompt import PromptLoadError, PromptSpec, build_user_message
from app.infrastructure.llm.schema import CoachAnalysisResponse, ParentResponse, merge_verdict

HARNESS_ID: Final = "parallel_split"


class ParallelSplitCoach:
    """`Coach` port implementation: two concurrent structured calls, one merged verdict."""

    harness_id: Final = HARNESS_ID

    def __init__(
        self,
        client: AsyncAnthropic | None,
        *,
        prompt: PromptSpec,
        model: str,
        parent_model: str | None = None,
        effort: str,
        timeout_seconds: float,
        thinking: dict[str, str] | None = None,
        metrics_sink: Callable[[CallMetrics], None] | None = None,
    ) -> None:
        if effort not in EFFORTS:
            raise ValueError(f"COACH_EFFORT must be one of {EFFORTS}, got {effort!r}")
        if prompt.coach_system is None or prompt.parent_system is None:
            raise PromptLoadError(
                f"Prompt v{prompt.version} has no coach/parent call sections for parallel_split"
            )
        self._client = client
        self._prompt = prompt
        self._model = model
        self._parent_model = parent_model or model
        self._effort = effort
        self._timeout = timeout_seconds
        self._thinking = thinking
        self._sink = metrics_sink
        self._coach_system = build_system(prompt.coach_system)
        self._parent_system = build_system(prompt.parent_system)

    @property
    def parent_model(self) -> str:
        return self._parent_model

    async def turn(self, coach_input: CoachInput) -> CoachVerdict:
        if self._client is None:
            self._emit("coach", self._model, time.perf_counter(), (0, 0, 0, 0), "no_api_key")
            self._emit(
                "parent", self._parent_model, time.perf_counter(), (0, 0, 0, 0), "no_api_key"
            )
            raise CoachUnavailable("The coach is unavailable.")
        user = build_user_message(coach_input)
        deadline = asyncio.get_running_loop().time() + self._timeout
        coach_task = asyncio.ensure_future(
            self._run(
                "coach", self._model, self._coach_system, user, CoachAnalysisResponse, deadline
            )
        )
        parent_task = asyncio.ensure_future(
            self._run(
                "parent", self._parent_model, self._parent_system, user, ParentResponse, deadline
            )
        )
        tasks = (coach_task, parent_task)
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            return merge_verdict(coach_task.result(), parent_task.result())
        except Exception:
            # A failed call, or a result that does not merge: never a partial verdict.
            raise CoachUnavailable("The coach is unavailable.") from None
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run[T: BaseModel](
        self,
        role: str,
        model: str,
        system: list[dict[str, Any]],
        user: str,
        schema: type[T],
        deadline: float,
    ) -> T:
        started = time.perf_counter()
        usage = (0, 0, 0, 0)
        outcome = "ok"
        try:
            assert self._client is not None  # noqa: S101 - checked in turn()
            loop = asyncio.get_running_loop()
            async with asyncio.timeout_at(deadline):
                response = await send_structured(
                    self._client,
                    model=model,
                    effort=self._effort,
                    thinking=self._thinking,
                    system=system,
                    user=user,
                    schema=schema,
                    sdk_timeout=max(deadline - loop.time(), 0.001),
                )
            usage = usage_of(response)
            return parsed_output(response, schema)
        except CallFailure as failure:
            outcome = failure.outcome
            raise
        except TimeoutError:
            outcome = "timeout"
            raise
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except Exception as exc:
            outcome = classify_error(exc)
            raise
        finally:
            self._emit(role, model, started, usage, outcome)

    def _emit(
        self, role: str, model: str, started: float, usage: tuple[int, int, int, int], outcome: str
    ) -> None:
        emit_metrics(
            CallMetrics(
                harness=HARNESS_ID,
                model=model,
                effort=self._effort,
                prompt_version=self._prompt.version,
                latency_ms=round((time.perf_counter() - started) * 1000, 1),
                input_tokens=usage[0],
                output_tokens=usage[1],
                cache_read_tokens=usage[2],
                cache_creation_tokens=usage[3],
                outcome=outcome,
                role=role,
            ),
            self._sink,
        )
