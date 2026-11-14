# Decision record: LLM harness for the role-play coach

**Status: NOT RUN.** The harness selection has not been executed. This file records the plan, the
rule and the commands only. **There are no results, no comparison table and no winner.** Nothing
below may be read as a measured claim about the coach.

Decided 2026-11-14 (user): the real-model eval runs (increments 25 to 27) are skipped for now: no
API key, no spend, no judge labels. The user will run them later. TASK.md section 13 criterion 6
("the harness selection has run ... comparison table ... the production configuration passes all
hard gates on the held-out test set") is therefore **not met**.

## Current production default (UNMEASURED)

| Setting | Value |
| --- | --- |
| Harness (`COACH_HARNESS`) | `single_call` |
| Model (`COACH_MODEL`) | `claude-opus-5-5` |
| Effort (`COACH_EFFORT`) | `low` |
| Prompt (`COACH_PROMPT_VERSION`) | `1` (`content/prompts/roleplay-turn.v1.md`, plus the fixed `INPUT_FORMAT_NOTE` in `infrastructure/llm/prompt.py`, which is part of the effective prompt v1) |
| Timeout (`LLM_TIMEOUT_SECONDS`) | 12 s, no retries |

This default is the starting point named in `.claude/rules/ai.md`, **not a selected winner**. It
has **NOT been measured against the real model**: its accuracy, judged quality, consistency,
latency (p50/p95), cost per turn and safety-flag recall are unknown. What is verified is only the
code path with a faked LLM, the local safety check and the deterministic rule re-application, and
the multiple-choice fallback when the model is missing, slow or fails.

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

## Commands (NOT RUN)

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

## To complete this record

When the runs are done, replace this file's status and add, for every stage: the comparison table
(accuracy, quality, consistency, latency p50/p95, cost per turn), the judge calibration result,
the chosen configuration and the test-set gate result, and link the reports in
`backend/evals/reports/`. Then set the winner in the settings defaults and `.env.example`.
