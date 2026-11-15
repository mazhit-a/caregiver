# Eval report: haiku-test (2026-11-15, test set)

| config | safety recall | accuracy | quality | consistency | schema fail | refusal | timeout | p50 / p95 / max ms | $/turn | $/lesson | $/lesson no cache |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| haiku-nothink-v1 | 100.0% (9/9) | 100.0% | n/a | 100.0% | 0.0% | 0.0% | 0.0% | 1778 / 2619 / 3755 (x1) | $0.00011 | $0.00033 | $0.00094 |

Accuracy is the mean of: mean per-goal accuracy, exact-score rate, argued accuracy, flag F1 (components with no applicable case are left out).

- haiku-nothink-v1: goals notice 100.0%, reassure 100.0%, offer 100.0%; exact score 100.0%; argued 100.0%; flag precision 100.0%, recall 100.0%

## Selection

Weights used: accuracy 0.7143, quality 0.0000, consistency 0.2857.
**Winner: haiku-nothink-v1**
1. haiku-nothink-v1: score 1.0000, p95 2619 ms
- note: Quality (judge) is absent for ALL candidates: its weight 0.3 is dropped and the others are renormalised to accuracy 0.7143 and consistency 0.2857.

## Failures

- haiku-nothink-v1 / e05_irritated_but_offers run 0:  tip: 2 sentences (max 1)
- haiku-nothink-v1 / l2_r2_irritated run 0:  parent_reaction: 4 sentences (max 2); tip: 2 sentences (max 1)
- haiku-nothink-v1 / l3_r1_strong run 0:  parent_reaction: 3 sentences (max 2)
- haiku-nothink-v1 / l3_r1_defends_and_corrects run 0:  parent_reaction: 3 sentences (max 2)
- haiku-nothink-v1 / l4_r1_strong run 0:  parent_reaction: 3 sentences (max 2)
- haiku-nothink-v1 / l4_r2_choice_only run 0:  parent_reaction: 3 sentences (max 2); tip: 2 sentences (max 1)
- haiku-nothink-v1 / e05_irritated_but_offers run 1:  parent_reaction: 4 sentences (max 2); tip: 2 sentences (max 1)
- haiku-nothink-v1 / l3_r1_strong run 1:  parent_reaction: 3 sentences (max 2); tip: 2 sentences (max 1)
- haiku-nothink-v1 / l4_r1_strong run 1:  parent_reaction: 3 sentences (max 2)
- haiku-nothink-v1 / l4_r2_choice_only run 1:  parent_reaction: 3 sentences (max 2); tip: 2 sentences (max 1)
- haiku-nothink-v1 / e05_irritated_but_offers run 2:  parent_reaction: 3 sentences (max 2); tip: 3 sentences (max 1)
- haiku-nothink-v1 / l2_r2_irritated run 2:  better_phrase: 26 words (max 25); parent_reaction: 3 sentences (max 2); tip: 2 sentences (max 1)
- haiku-nothink-v1 / l4_r1_strong run 2:  tip: 2 sentences (max 1)
- haiku-nothink-v1 / l4_r2_choice_only run 2:  parent_reaction: 3 sentences (max 2); tip: 2 sentences (max 1)

Prices retrieved on 2026-11-14: RE-CHECK BEFORE EVERY REAL RUN. Defaults were supplied from the claude-api model table on the retrieval date, not fetched by code. Cache-write prices and the haiku cache-read price are DERIVED (write = 1.25 x input, haiku read = 5% of input, the same ratio as opus and sonnet), not published figures. Prices apply to prompts up to 100K tokens.
