"""Cost estimate and the confirmation gate. A real run never starts without both.

estimate = calls x tokens x price, with calls = cases x runs per configuration (cache hits are
free and not counted). Tokens come from MEASURED averages when given, else from a table estimate:
prompt text length / 4 (a rough chars-per-token heuristic) plus a per-effort output allowance.
The estimate shown for the gate is the WORST CASE (no cache hits); the cached figure is printed too.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

from app.infrastructure.llm.parallel_split import HARNESS_ID as PARALLEL_SPLIT
from app.infrastructure.llm.prompt import (
    INPUT_FORMAT_NOTE,
    PromptLoadError,
    build_user_message,
    load_prompt,
)
from evals.case import EvalCase
from evals.client import CoachConfig
from evals.metrics import PriceTable

CHARS_PER_TOKEN: Final = 4.0
# Output allowance per effort (assumption; replace by measured values after a first run).
OUTPUT_TOKENS_BY_EFFORT: Final[dict[str, int]] = {
    "low": 300,
    "medium": 700,
    "high": 1500,
}
DEFAULT_OUTPUT_TOKENS: Final = 700
# parallel_split parent call: only parentReaction + parentMood, assumed half the coach allowance.
PARENT_OUTPUT_DIVISOR: Final = 2


@dataclass(frozen=True)
class TokenEstimate:
    """Tokens per call. For `parallel_split` this is the COACH call and `parent` is the PARENT
    call (its own prompt, model and output size); both calls are made on every turn."""

    input_tokens: int  # uncached input per call (prompt + user message)
    output_tokens: int
    cacheable_input_tokens: int = 0  # part of the input that a warm cache serves at read price
    parent: "TokenEstimate | None" = None


@dataclass(frozen=True)
class ConfigEstimate:
    config_name: str
    model: str
    calls: int  # real model calls (parallel_split: two per turn)
    tokens: TokenEstimate
    usd: float  # no cache hits
    usd_with_cache: float  # the static prefix read from cache on every call but the first
    turns: int = 0  # cases to run; equals `calls` except for parallel_split
    parent_model: str | None = None  # parallel_split only: the model of the parent call


@dataclass(frozen=True)
class CostEstimate:
    lines: tuple[ConfigEstimate, ...]
    prices_retrieved_on: str

    @property
    def calls(self) -> int:
        return sum(line.calls for line in self.lines)

    @property
    def total_usd(self) -> float:
        return sum(line.usd for line in self.lines)

    @property
    def total_usd_with_cache(self) -> float:
        return sum(line.usd_with_cache for line in self.lines)


def _tokens(system: str, note_chars: int, user_chars: Sequence[int], effort: str) -> TokenEstimate:
    prefix = int((len(system) + note_chars) / CHARS_PER_TOKEN)
    mean_user = int(sum(user_chars) / len(user_chars) / CHARS_PER_TOKEN) if user_chars else 0
    return TokenEstimate(
        input_tokens=prefix + mean_user,
        output_tokens=OUTPUT_TOKENS_BY_EFFORT.get(effort, DEFAULT_OUTPUT_TOKENS),
        cacheable_input_tokens=prefix,
    )


def table_token_estimate(
    config: CoachConfig, cases: Sequence[EvalCase], content_dir: Path
) -> TokenEstimate:
    """Table estimate from the real prompt file and the real user-message builder. For
    `parallel_split` the estimate is per role: the coach call (`coach_system`) with `.parent` the
    parent call (`parent_system`, whose output is only the reaction and mood: assumed half of the
    coach allowance). Raises `PromptLoadError` for a prompt version without the call sections."""
    prompt = load_prompt(content_dir, config.prompt_version)
    user = [len(build_user_message(c.to_coach_input())) for c in cases]
    if config.harness != PARALLEL_SPLIT:
        note = len(INPUT_FORMAT_NOTE) if prompt.input_format_note else 0
        return _tokens(prompt.system, note, user, config.effort)
    if prompt.coach_system is None or prompt.parent_system is None:
        raise PromptLoadError(
            f"Prompt v{prompt.version} has no coach/parent call sections for parallel_split"
        )
    coach = _tokens(prompt.coach_system, 0, user, config.effort)
    parent = _tokens(prompt.parent_system, 0, user, config.effort)
    parent = replace(parent, output_tokens=max(parent.output_tokens // PARENT_OUTPUT_DIVISOR, 1))
    return replace(coach, parent=parent)


def _call_usd(model: str, t: TokenEstimate, n: int, prices: PriceTable) -> tuple[float, float]:
    """(no cache, warm cache) USD for `n` calls of `t` on `model`."""
    p = prices.price(model)
    out = t.output_tokens * p.output_per_mtok
    full = (t.input_tokens * p.input_per_mtok + out) * n / 1_000_000
    uncached_part = t.input_tokens - t.cacheable_input_tokens
    warm = (
        (uncached_part * p.input_per_mtok + t.cacheable_input_tokens * p.cache_read_per_mtok + out)
        * n
        / 1_000_000
    )
    return full, min(warm, full)


def estimate_config(
    config: CoachConfig, calls: int, tokens: TokenEstimate, prices: PriceTable
) -> ConfigEstimate:
    """`calls` = turns to run. A parallel_split turn is two model calls, each priced with its own
    model (`config.model` for the coach call, `config.parent_model or config.model` for the
    parent call) and its own token estimate."""
    full, warm = _call_usd(config.model, tokens, calls, prices)
    if tokens.parent is None:
        return ConfigEstimate(config.name, config.model, calls, tokens, full, warm, calls)
    parent_model = config.parent_model or config.model
    p_full, p_warm = _call_usd(parent_model, tokens.parent, calls, prices)
    return ConfigEstimate(
        config.name,
        config.model,
        calls * 2,
        tokens,
        full + p_full,
        warm + p_warm,
        calls,
        parent_model,
    )


def estimate_run(
    items: Sequence[tuple[CoachConfig, int, TokenEstimate]], prices: PriceTable
) -> CostEstimate:
    """`items`: (config, number of model calls to make, tokens per call)."""
    return CostEstimate(
        tuple(estimate_config(c, n, t, prices) for c, n, t in items), prices.retrieved_on
    )


def format_estimate(est: CostEstimate, runs: int, case_count: int) -> str:
    rows = [
        f"Cost estimate: {case_count} cases x {runs} runs x {len(est.lines)} configs "
        f"(cache hits not counted; prices retrieved {est.prices_retrieved_on}, re-check them)"
    ]
    for ln in est.lines:
        if ln.tokens.parent is None:
            shape = (
                f"{ln.calls:>5} calls x "
                f"{ln.tokens.input_tokens} in / {ln.tokens.output_tokens} out tokens"
            )
        else:
            p = ln.tokens.parent
            shape = (
                f"{ln.turns:>5} turns x 2 calls ({ln.calls} calls): coach {ln.model} "
                f"{ln.tokens.input_tokens} in / {ln.tokens.output_tokens} out, parent "
                f"{ln.parent_model} {p.input_tokens} in / {p.output_tokens} out tokens"
            )
        rows.append(
            f"  {ln.config_name:<24} {ln.model:<20} {shape} = "
            f"${ln.usd:.4f} (about ${ln.usd_with_cache:.4f} with prompt-cache hits)"
        )
    rows.append(
        f"  TOTAL {est.calls} calls: up to ${est.total_usd:.4f} "
        f"(about ${est.total_usd_with_cache:.4f} with cache hits)"
    )
    return "\n".join(rows)


@dataclass(frozen=True)
class Confirmation:
    approved: bool
    reason: str


def confirm_run(
    est: CostEstimate,
    *,
    yes: bool,
    max_cost_usd: float | None,
    interactive: bool,
    input_fn: Callable[[str], str] = input,
) -> Confirmation:
    """Gate before any real call (compared on the worst-case total).

    - Over the cap: refused, whatever else was said.
    - `--yes` from a non-interactive session counts only with a `--max-cost-usd` the estimate is
      below; an interactive `--yes` is accepted.
    - No `--yes`: a prompt, and only "y" / "yes" approves. Non-interactive: refused.
    """
    total = est.total_usd
    if max_cost_usd is not None and total > max_cost_usd:
        return Confirmation(
            False, f"estimate ${total:.4f} exceeds --max-cost-usd ${max_cost_usd:.4f}"
        )
    if yes:
        if interactive or max_cost_usd is not None:
            return Confirmation(True, "approved by --yes")
        return Confirmation(False, "--yes from a non-interactive session needs --max-cost-usd")
    if not interactive:
        return Confirmation(
            False, "confirmation needed but the session is not interactive (see --max-cost-usd)"
        )
    answer = input_fn(f"Run {est.calls} real model calls for up to ${total:.4f}? [y/N] ")
    if answer.strip().lower() in {"y", "yes"}:
        return Confirmation(True, "confirmed")
    return Confirmation(False, "not confirmed")
