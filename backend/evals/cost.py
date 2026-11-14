"""Cost estimate and the confirmation gate. A real run never starts without both.

estimate = calls x tokens x price, with calls = cases x runs per configuration (cache hits are
free and not counted). Tokens come from MEASURED averages when given, else from a table estimate:
prompt text length / 4 (a rough chars-per-token heuristic) plus a per-effort output allowance.
The estimate shown for the gate is the WORST CASE (no cache hits); the cached figure is printed too.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.infrastructure.llm.prompt import INPUT_FORMAT_NOTE, build_user_message, load_prompt
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


@dataclass(frozen=True)
class TokenEstimate:
    input_tokens: int  # uncached input per call (prompt + user message)
    output_tokens: int
    cacheable_input_tokens: int = 0  # part of the input that a warm cache serves at read price


@dataclass(frozen=True)
class ConfigEstimate:
    config_name: str
    model: str
    calls: int
    tokens: TokenEstimate
    usd: float  # no cache hits
    usd_with_cache: float  # the static prefix read from cache on every call but the first


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


def table_token_estimate(
    config: CoachConfig, cases: Sequence[EvalCase], content_dir: Path
) -> TokenEstimate:
    """Table estimate from the real prompt file and the real user-message builder."""
    system = load_prompt(content_dir, config.prompt_version).system
    prefix = int((len(system) + len(INPUT_FORMAT_NOTE)) / CHARS_PER_TOKEN)
    user = [len(build_user_message(c.to_coach_input())) for c in cases]
    mean_user = int(sum(user) / len(user) / CHARS_PER_TOKEN) if user else 0
    return TokenEstimate(
        input_tokens=prefix + mean_user,
        output_tokens=OUTPUT_TOKENS_BY_EFFORT.get(config.effort, DEFAULT_OUTPUT_TOKENS),
        cacheable_input_tokens=prefix,
    )


def estimate_config(
    config: CoachConfig, calls: int, tokens: TokenEstimate, prices: PriceTable
) -> ConfigEstimate:
    p = prices.price(config.model)
    out = tokens.output_tokens * p.output_per_mtok
    full = (tokens.input_tokens * p.input_per_mtok + out) * calls / 1_000_000
    uncached_part = tokens.input_tokens - tokens.cacheable_input_tokens
    warm = (
        (
            uncached_part * p.input_per_mtok
            + tokens.cacheable_input_tokens * p.cache_read_per_mtok
            + out
        )
        * calls
        / 1_000_000
    )
    return ConfigEstimate(config.name, config.model, calls, tokens, full, min(warm, full))


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
        rows.append(
            f"  {ln.config_name:<24} {ln.model:<20} {ln.calls:>5} calls x "
            f"{ln.tokens.input_tokens} in / {ln.tokens.output_tokens} out tokens = "
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
