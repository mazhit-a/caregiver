# Decision: adopt the content package (Kelper spec, 24-screen lesson 1)

Date: 2026-11-15. Source: `context/design/content-package/` (never edited). Plan: `context/frontend/PLAN-04-content.md`.

## What was adopted, kept, or left out

| File | Class | Decision |
| --- | --- | --- |
| `spec.md` | package newer | Replaces `docs/design-spec.md` in place (v3.2: Kelper, Ollie, brand book). History is in git. |
| `quiz.json` | package newer | Take `speaker: "ollie"` on the two interstitials (done with the lesson increments). No tag change. |
| `lessons/m1_l1.json` | package newer, with patches | 24-screen rewrite adopted after the patches below. Keep `day2`, `fallbackScenarios`, `recapForNextLesson`, `pattern`. |
| `lessons/m1_l2..l5` | repo only | Keep in the old schema (`learn`, legacy scenario). Converted later when the owner supplies real lessons. |
| `plan-rules.json` | repo newer | Keep ours (v5); v6 only changes `m1_l1.minutes` to 9 and the note. |
| `funnel-copy.json`, `pricing.json` | repo newer | Keep ours. Do not re-add the package's `savePlan` block (server session). |
| `phrases.json`, `prompts/roleplay-turn.md`, `evals/roleplay-evals.json` | identical | Nothing. |
| `state-contract.md`, `funnel-qa.md`, content `README.md` | repo = package + notes | Keep ours. |

## Patches applied to the owner's `m1_l1.json`

1. Add `setupVariantMap` and `optionsVariantMap` on the scenario so `both` and `not_yet` resolve.
2. Add `bodyVariantMap` on `tools`.
3. `plan.ifThen.resetFrom`: `s6_fifth_time` becomes `you`.
4. Scenario verdict `try` becomes `try_again`.
5. Reset options become `[label, planText]` pairs (code never lower-cases content).
6. Remove hard-coded gender and family wording (she/her/daughter/Dad); use `{recipient}`/`{object}` or neutral text.
7. Rewrite the singular-they sentences with `{recipient}` as the subject.
8. Intro says "about 9 minutes".
9. Optional: `part` missing on `setup`, `scenario`, `wrap` (noted only).

## Not adopted

`HANDOFF.md` and `CLAUDE.md.template` describe the localStorage / Next.js / Vercel design. TASK.md wins on anything technical. The folder stays as an archive; the HANDOFF lesson table is a reference for the frontend lesson screens.

## Brand and rename

Product is Kelper; the guide is Ollie (sea otter, not a nurse). Docs and code strings renamed in C1. Stripe `PRODUCT_NAME` is "Kelper"; `stripe_setup.py` renames an existing product when its name differs. The script was not run; run it once with a test key at deploy time. `PRODUCT_KEY` and `pcn_key` stay (internal lookup keys). Ollie is never shown on crisis, payment, medical, documents, gentle-exit or demo-banner screens.
