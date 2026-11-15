# Decision record: LLM harness for the role-play coach

**Status: PARTIAL, a budget-limited selection (2026-11-15).** The coach default is now
`claude-haiku-5-5`, thinking disabled, effort low, prompt v1, `single_call`. It passed every hard
gate on the dev set and on the held-out test set. The full staged search of this record was **not**
run: the user had no budget for the Opus runs and has no judge labels, so **quality (judge) was
never measured** and Opus was never measured under the same 3-run protocol. Read the result as
"Haiku is good enough on the code-based graders", not as "Haiku is the best coach".

## Result

All runs: real model calls, prompt v1 unless noted, `single_call`, dev = 32 cases, test = 11 cases
(held out, run once). Reports: `backend/evals/reports/` (the `.md` files named below are committed).
Prices are from `evals/data/prices.json` (retrieved 2026-11-14, cache-write and Haiku cache-read
prices derived).

| Config | Set | Runs | Safety recall | Accuracy | Consistency | p95 latency | $/turn | Report |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opus-low (the old default), grader without label rule | dev | 1 | 100% (3/3) | 98.9% | n/a | 3.7 s | $0.0051 | `2026-11-15-v1-regrade.md` |
| opus-low, prompt v2 | dev | 1 | 100% (3/3) | 98.9% | n/a | 3.2 s | $0.0059 | `2026-11-15-v2-regrade.md` |
| haiku-low | dev | 3 | 100% (9/9) | 98.9% | 96.9% | 5.65 s (**fails the 5 s gate**) | $0.00018 | `2026-11-15-haiku.md` |
| **haiku-nothink** | dev | 3 | 100% (9/9) | 97.5% | 90.6% | 3.25 s | $0.00012 | `2026-11-15-haiku.md` |
| **haiku-nothink** | **test** | 3 | **100% (9/9)** | **100%** | **100%** | 2.6 s | $0.00011 | `2026-11-15-haiku-test.md` |

Hard gates for haiku-nothink on the test set: safety recall 100%, schema failures 0%, refusals 0%,
timeouts 0%, p95 2.6 s (gate 5 s): **all pass**. Cost per lesson (3 turns): about $0.0003 with
caching, against about $0.015 for Opus.

Observations
- Accuracy is the same across Opus v1, Opus v2 and Haiku within one-run noise; the only recurring
  miss on every model is the case `l5_r2_facts_only` (argued), whose expected value is marked
  "needs content review" in the case file.
- Format rules (parent reaction <= 2 sentences, tip <= 1 sentence, better phrase <= 25 words) fail
  often on Haiku (mostly the parent reaction and tip length) and less on Opus; they do not affect
  scores or safety. Prompt v2 halved the format failures on Opus (16 to 8 failing cases) at about
  16% more cost per turn; v2 was not tried on Haiku.
- The grader rule "better phrase must contain the label" was removed (commit `5d936fb`): the
  prompt's own examples and the dataset's model answers never name the parent.
- `thinking: {"type": "disabled"}` is accepted by the API for Haiku 5.5 (the runs succeeded).

## Deviations from the approved rule (user-approved by budget, 2026-11-15)

1. Selection was done without the judge, so the 0.3 quality weight is dropped and the others are
   renormalised (accuracy 0.714, consistency 0.286). The rule said not to select a final winner
   without the judge. **Quality is unmeasured.**
2. Opus was run once per case on the dev set only (no consistency number, no test-set run), and
   Sonnet, harness variants and the parallel split were not run at all. The staged plan below is
   unfinished.
3. Safety recall rests on 3 medical/crisis cases x 3 runs per set: small. A miss on a larger set
   would change the decision. The code path that stops crisis words before any model call is
   unaffected by the model choice.

To revisit later (when there is budget): `--stage prompt` for Opus v1 vs v2 at 3 runs (about
$1.1 to $2.2), the judge calibration below, and the full test-set comparison. The old default
stays available: `COACH_MODEL=claude-opus-5-5`, `COACH_THINKING=` (empty).

## Current production default

| Setting | Value |
| --- | --- |
| Harness (`COACH_HARNESS`) | `single_call` |
| Model (`COACH_MODEL`) | `claude-haiku-5-5` |
| Effort (`COACH_EFFORT`) | `low` |
| Thinking (`COACH_THINKING`) | `disabled` (empty keeps the model default; set it empty for models that need thinking) |
| Prompt (`COACH_PROMPT_VERSION`) | `1` (`content/prompts/roleplay-turn.v1.md`, plus the fixed `INPUT_FORMAT_NOTE` in `infrastructure/llm/prompt.py`) |
| Timeout (`LLM_TIMEOUT_SECONDS`) | 12 s, no retries |

## Approved selection rule (fixed before any run)

1. Hard gates (all must hold): safety recall 100%; schema failures <= 0.5%; timeout rate 0% at
   12 s; p95 latency <= 5 s.
2. Among survivors, rank by `0.5 x accuracy + 0.3 x quality + 0.2 x consistency`, each normalised
   0 to 1. Weights approved by the product owner on 2026-11-14.
3. If the top two are within 0.02, pick the lower p95 latency, then the lower cost.
4. The winner (harness, model, effort, prompt version) is written to the settings defaults and
   into this file with the comparison table.

Not yet confirmed by the user: the definition of the *accuracy* number. The implementation
(`backend/evals/rule.py`) uses the mean of per-goal accuracy, exact-score rate, argued accuracy and
flag F1 (components without applicable cases are left out). The weights are approved; this
composite is the build agent's and needs confirmation. Also not confirmed: the eval budget.

## Staged search plan

1. **Prompt:** v1 vs v2 (XML plus few-shot) on `claude-opus-5-5`, effort low, dev set.
2. **Model x effort:** best prompt x {haiku-nothink, haiku-low, sonnet-low, sonnet-medium,
   opus-low, opus-medium}, dev set. (`haiku-nothink` assumes `thinking={"type": "disabled"}`:
   verify against the API docs first.)
3. **Harness shape:** top 2 x {`single_call`, `parallel_split`}, dev set, with `--prompt-version 2`
   (the only version with the coach/parent sections). Open question: also try a cheaper parent
   model (the `+parallel_split:haiku` variant; default: no).
4. **Final:** top 3 on the held-out **test** split (use it once per final comparison), 3 runs
   each, live latency at concurrency 1 then 4 (`--no-cache`). Then apply the rule.

Dataset: `backend/evals/datasets/golden.jsonl`, 43 cases (14 package + 29 lesson cases written by
the build agent, all awaiting content-owner review). Deterministic split by
`sha256("pcn-eval-v2:" + id)`: 32 dev, 11 test (`--validate-only`). This is below the >= 120 cases /
>= 40 test target in the plan; a generated set was not built.

## Commands (reference; the runs above used the `haiku` and `haiku-test` stages)

All from `backend/`. Always `--dry-run` first; real runs ask for confirmation. Worst-case
estimates come from `--dry-run` with `evals/data/prices.json` retrieved 2026-11-14; token counts
are table estimates and the parent-call output is assumed to be half the coach allowance until
measured. **Prices for cache-write (1.25x input) and haiku cache-read (5% of input) are derived,
not published: verify before any real run.**

| Stage | Command | Calls | Worst case |
| --- | --- | --- | --- |
| prompt (dev) | `uv run python -m evals.run --stage prompt --set dev --dry-run` | 192 | <= $2.57 |
| model-effort (dev) | `uv run python -m evals.run --stage model-effort --set dev --prompt-version 2 --dry-run` | 576 | <= $5.95 |
| harness (dev) | `uv run python -m evals.run --stage harness --set dev --prompt-version 2 --dry-run` | 288 | <= $3.86 |
| harness, haiku parent variant (dev) | `--config opus-low+parallel_split:haiku ...` | 480 | <= $5.29 |
| final (test, 3 runs, concurrency 1 then 4 with `--no-cache`) | `uv run python -m evals.run --config <top 3> --set test --yes --max-cost-usd 2` | about 100 | about $1.3 for the harness pair |

Remove `--dry-run` to run for real (asks for confirmation; `--yes` needs `--max-cost-usd`).
`--judge` adds roughly $2 per dev stage and is refused until a judge calibration report passes.
Pre-demo gate after the selection: `uv run python -m evals.run --config production --set test`.

## Judge calibration prerequisite

The judge (`backend/evals/prompts/judge.v1.md`) may only be used after it agrees with **human**
scores. Required: at least 20 labelled outputs (aim for 25 or more, mixed good, middling and weak,
at least 3 labels of 2 or below per rubric item), agreement of at least 80% overall **and per
rubric item** (stricter than the plan: confirm). **Code never writes these labels and a model must
not label them** (that would calibrate the judge against itself).

Guide: [`backend/evals/LABELING.md`](../../backend/evals/LABELING.md). Draft rows from cached
outputs: `uv run python -m evals.labels draft --config production`; then label by hand and run
`uv run python -m evals.calibrate`. Without a judge, quality is absent and selection renormalises
the remaining weights, which departs from the approved 0.5/0.3/0.2 rule: do not select a final
winner without the judge.

## To complete this record (when the full search is run)

When the runs are done, replace this file's status and add, for every stage: the comparison table
(accuracy, quality, consistency, latency p50/p95, cost per turn), the judge calibration result,
the chosen configuration and the test-set gate result, and link the reports in
`backend/evals/reports/`. Then set the winner in the settings defaults and `.env.example`.
