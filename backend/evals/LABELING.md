# Labelling coach outputs for judge calibration (a task for a person)

The judge (`prompts/judge.v1.md`) may only be used after it agrees with human scores on at least
20 outputs: `python -m evals.calibrate` must report agreement of at least 80%. **Code never writes
these labels.** Do not let a model label them: that would calibrate the judge against itself.

## What to do
1. Get outputs to label. After a manual `python -m evals.run` (so the result cache holds coach
   outputs): `python -m evals.labels draft --config production` writes
   `datasets/human_labels.draft.jsonl` (no model call). Or copy real outputs by hand using the format
   in `datasets/human_labels.template.jsonl`.
2. Aim for 25 or more rows, mixed on purpose: some clearly good, some middling, and at least 3 clearly
   weak per rubric item (a file of only good outputs cannot test a judge; the validator requires it).
3. For each row set `human` to three whole numbers 1 to 5 and `labeler` to your name:
   - `betterPhrase`: does it hit ALL THREE goals (notice, reassure, offer) for THIS parent line, and
     sound like something a tired caregiver would say? 5 = all three, natural; 3 = two goals or stiff;
     1 = at most one goal, ignores the line, or argues.
   - `tip`: warm, specific to what the caregiver said, and accurate. 5 = all three; 1 = shaming,
     wrong about the reply, or empty.
   - `parentReaction`: in character for a person with dementia in this mood and consistent with how
     good the reply was. 5 = yes; 1 = out of character or contradicts the reply's quality.
   Score before reading the judge's output, and do not look at it while labelling.
4. Save as `datasets/human_labels.jsonl` (remove the template rows; rows with `"template": true`
   are rejected). Check: `python -m evals.labels validate`.
5. Calibrate (costs money, asks for confirmation; see `--dry-run` and `--max-cost-usd`):
   `python -m evals.calibrate --dry-run`, then `python -m evals.calibrate`.
   Exit 0 = pass. The report goes to `reports/calibration/`.
6. Below 80%: read the disagreements in the report (`rows`), fix `prompts/judge.v1.md` (or create
   `judge.v2.md` and pass `--prompt-version v2`), and calibrate again. Editing the prompt file
   invalidates the existing report.

## Format (one JSON object per line, camelCase)
See `evals/labels.py` for the schema. Row text is stored in the file, so use invented or
anonymised lines only: no real names, diagnoses or medications.
