# Parent Care Navigator

A web course for adult children caring for a parent with dementia. A short quiz builds a personal
plan, a paywall (Stripe test mode, or a no-Stripe demo mode) opens a set of lessons that are
released over time, and an AI role-play coach lets the caregiver practise one hard sentence at a
time. Return visits (Today screen, check-ins, a shareable care card, a visit sheet) and renewal
complete the loop. Built for a hackathon demo that judges use **without logging in**.

> We teach and organize. We don't give medical advice.

**Status of this repository: backend only.** The React frontend is a later task. Everything in
this README that talks about "the frontend" describes the contract the backend expects.

**Not yet verified: the quality of the AI coach.** All automated tests run against a faked LLM
and a faked Stripe. The real model has not been evaluated (the harness selection in
`docs/decisions/llm-harness.md` is **NOT RUN**), and the production default has not been measured.
See [Evals](#evals-not-yet-run).

## Contents

1. [Architecture](#architecture)
2. [Real vs test mode](#real-vs-test-mode)
3. [Privacy model](#privacy-model)
4. [Run locally](#run-locally)
5. [Deploy on the VPS](#deploy-on-the-vps)
6. [Manual Stripe test-mode run](#manual-stripe-test-mode-run-pending-user-action)
7. [Evals (not yet run)](#evals-not-yet-run)
8. [Where to change content](#where-to-change-content)
9. [API overview](#api-overview)
10. [Before launch checklist](#before-launch-checklist)
11. [Known limitations](#known-limitations)

## Architecture

```
            browser (React app, later task)
                      |  HTTPS
                  +---v---+        +-------------------+
                  | Caddy |------->| api (FastAPI)     |------> Anthropic API (role-play coach)
                  +-------+ /api/* | one uvicorn worker|------> Stripe (test mode)
                                   +---------+---------+
                                             |
                                       +-----v-----+
                                       | Postgres  |
                                       +-----------+
   content/  (JSON + Markdown, mounted read-only into api)     evals/ = backend/evals (manual)
```

`docker compose`: `db` (postgres:16) - `api` (migrates on start, then uvicorn) - `caddy` (HTTPS,
security headers, 64 KB body limit on `/api/*`). The `web` service arrives with the frontend.

**Layers (Clean Architecture, `backend/app/`)**

| Layer | Holds | May import |
| --- | --- | --- |
| `domain/` | entities, value objects, policies per feature (plan builder, safety check, score rules, subscription state machine, unlock formula). Pure Python: no I/O, no framework, no clock. | nothing outward |
| `application/` | one use case per user action, `ports.py` (Protocols for repositories, clock, LLM, payments), DTOs | `domain` |
| `infrastructure/` | adapters: `config.py` (Settings), `db/` (async SQLAlchemy, mappers, unit of work), `llm/` (Anthropic), `payments/` (Stripe), `content/` (loader and schemas), `clock.py`, `logging.py` | `application`, `domain` |
| `presentation/` | `api/` v1 routers, request and response schemas, `deps.py` (session auth, subscription gate, RBAC-style dependencies), `error_handlers.py` | `application`, `domain` |
| `main.py` | composition root: wires adapters to ports | everything |

Rules that matter when you change code:

- Dependencies point inward only. `lint-imports` (config: `backend/.importlinter`) fails the
  build otherwise.
- Request path: router (parse, call one use case, map DTO to schema) -> use case (repositories,
  domain, commit through the unit of work, gateways) -> domain (rules, invariants).
- Subscription status changes only through the `Subscription` entity (a state machine). Stripe
  webhooks are the source of truth for Stripe sessions and are idempotent by event id.
- Access to app endpoints goes through the gate dependency in `presentation/api/deps.py`; no
  inline status checks in routes.
- Time comes from the injected `Clock` port (real now plus the session's demo offset), never
  `datetime.now()` in domain or application code. That keeps "Simulate next day" and renewals
  consistent.
- Placeholders such as `{recipient}` are rendered server-side in one place
  (`domain/shared/labels.py`); the API never returns an unfilled `{...}`.
- Endpoints are `async def`, return Pydantic schemas (camelCase JSON) and errors share one shape:
  `{"error": {"code", "message", "details"}}`.
- All Python is type-annotated (`mypy --strict`), formatted and linted with `ruff`.

**Safety (hard rules, enforced in code)**

- The local safety check (`domain/safety`, terms from `content/safety-terms.json`) runs before
  every LLM call. A crisis match never reaches the model; the response carries crisis resources.
- The coach's scoring rules are re-applied in code after the model answers (score = true goals,
  capped at 2 when the caregiver argued; `medical` returns a fixed tip with score 0).
- Any LLM failure (12 s timeout, API error, refusal, invalid JSON) returns a multiple-choice
  fallback from the lesson file. The UI never waits on the model.

**Where content lives:** `content/` holds all wording, rules and numbers (see
[Where to change content](#where-to-change-content)). `docs/design-spec.md` is the product spec,
`TASK.md` the technical source of truth, `context/PLAN.md` and `context/PROGRESS.md` the
increment plan and what was verified.

## Real vs test mode

| Part | Real | Test / demo | What is verified today |
| --- | --- | --- | --- |
| Plan from quiz | Real rules from `content/plan-rules.json` | - | Persona A, B, C tests give the exact expected plans. |
| AI role-play | Real LLM call (Anthropic) | Multiple-choice fallback when the LLM fails, is slow, or no key is set | Tests use a **faked LLM**. The fallback path is tested (no key, forced timeout). **The real model has NOT been evaluated**: accuracy, quality, latency and cost of the coach are unmeasured. |
| Payments | - | Stripe test mode (card 4242 4242 4242 4242), or demo mode with no Stripe | Tests use a **faked Stripe**. The real Stripe flow has **not** been run: see the [manual checklist](#manual-stripe-test-mode-run-pending-user-action). |
| Renewal | Stripe really issues the renewal invoice | Triggered by moving a Stripe Test Clock (Stripe path) or the app clock (demo path) | Demo renewal and webhook handling are tested with fakes. Test Clock behaviour against real Stripe is unverified. |
| Time | Real time | "Simulate next day" and "Jump to renewal" (labelled demo controls, `DEMO_CONTROLS=true`) | Tested. |
| Care card link | Real, public, revocable | - | Tested. |

Live Stripe keys are refused at startup (test keys only). With no `ANTHROPIC_API_KEY` the app runs
and every role-play turn uses the fallback (a warning is logged at startup). With the dummy Stripe
key from `.env.example` (or none) the app runs in demo mode only.

## Privacy model

**What is stored**

- An anonymous session (token, timezone, app-clock offset, optional display name), no account,
  no email, no name required.
- Derived quiz tags and the built plan (a stored snapshot). Plan snapshots are never reshuffled by
  later content edits.
- Lesson progress, scenario answers, if-then plans, check-ins, scores per role-play turn, and
  phrases the caregiver explicitly saved.
- Subscription state and history. Stripe receives only the plan id, the amount and the internal
  session UUID: no quiz answers, no names.
- Anonymous event counts (`events`: whitelisted names, no free text) for funnel metrics
  (`backend/scripts/metrics.sql`).
- A published care card holds only the whitelisted fields in TASK.md section 6.12: never quiz
  answers, diagnosis or medications.

**What is purged**

- Raw Q3 and Q5 quiz answers are deleted when the subscription starts; the derived tags and the
  plan remain. The quiz is then locked.
- "Gentle exit" (`POST /api/exit/gentle`) cancels any Stripe subscription, revokes the care card
  and deletes every row of the session (cascade). If cancelling at Stripe fails the answer is
  `503 billing_cancel_failed` and nothing is deleted. `stripe_events` keeps only event id, type and
  timestamps (no link to the session).

**What is never stored or logged**

- **Role-play text.** The caregiver's replies and the model's output (parent line, tip, better
  phrase) are never persisted or logged. Only scores and phrases the user chooses to save are kept.
  `finish` takes the better phrases from the client for exactly that reason.
- Request bodies on quiz, role-play, profile and visit-sheet routes are not logged. The access log
  is the app's own (`app.request`); uvicorn's access log is off. Query strings are never logged.
- SDK/library loggers (`anthropic`, `sqlalchemy`, `asyncpg`, `httpx`, `httpcore`, `stripe`) are
  pinned at WARNING because they can log request bodies or bound parameters at DEBUG.
- No third-party trackers.

**Care card links are bearer secrets.** Anyone with the link can read the card until it is revoked.
The card id is a long random value; `/api/cards/{id}` is redacted in logs and rate limited per
client. Revoked cards return `410`.

**Session token.** The token lives in the browser (header `X-Session-Token`). If the user clears
their browser data or switches device, the session cannot be recovered (no account). The
frontend should say so.

**Copy change required (content owner).** The older product copy says "Your answers stay in this
browser". That is no longer true: answers are stored on the server, tied to the anonymous session.
It must read: **"Saved privately to this session. No account, no name needed."** Search
`content/` and the frontend for the old sentence before launch.

## Run locally

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), Python 3.12, optionally the
[Stripe CLI](https://stripe.com/docs/stripe-cli).

```bash
cp .env.example .env                       # dummy values; add real TEST keys only to your local .env

# Database for development and tests (the dev override publishes it on host port 55432)
docker compose up -d db

cd backend
uv sync                                    # install dependencies
# api on the host talks to the published port, not to the compose service name:
export DATABASE_URL=postgresql+asyncpg://pcn:pcn@localhost:55432/pcn
uv run alembic upgrade head                # migrations (head is 0022)
uv run uvicorn app.main:create_app --factory --reload   # http://localhost:8000/api/docs
```

`.env.example` points `DATABASE_URL` at the compose service name `db` (for the api container) and
`TEST_DATABASE_URL` at `localhost:55432`. The test database `pcn_test` is created on demand by the
test suite.

**Full stack in Docker** (db, api, caddy; plain HTTP on port 80 when `SITE_ADDRESS` is empty):

```bash
docker compose up --build -d
curl -s http://localhost/api/health        # {"status":"ok"}
```

**Tests and lints** (all from `backend/`; no network, LLM and Stripe are faked):

```bash
uv run pytest -v                           # default suite (1003 tests); excludes slow tests
uv run pytest -m slow                      # 2 slow tests (real-time hang/timeout case, ~13 s)
uv run lint-imports                        # layer rules
uv run mypy --strict app scripts evals     # types
uv run ruff check . && uv run ruff format --check .
../scripts/check_secrets.sh                # tracked/untracked files hold no real-looking secrets
../scripts/check_secrets.sh --history      # also every added line in git history
```

**Stripe locally (test mode only)**

```bash
# 1. Put a Stripe TEST key in .env (STRIPE_SECRET_KEY=sk_test_...). Live keys are refused.
# 2. Create products, prices and coupons once; writes their ids into content/pricing.json:
cd backend && uv run python -m scripts.stripe_setup     # scripts/stripe_setup.py, idempotent
# 3. Forward webhooks and copy the printed signing secret into STRIPE_WEBHOOK_SECRET in .env:
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

While `content/pricing.json` still contains `REPLACE` ids and a real test key is set, the app refuses
to start. Unset `STRIPE_SECRET_KEY` (or keep `sk_test_dummy`) to use demo mode only. The setup
script is committed; the ids it writes into `pricing.json` are test-mode ids and may be committed.

## Deploy on the VPS

Pending user action; nothing here has been run on a real server. The stack itself was verified from
a clean `git clone` (increment 41 acceptance run): db, api and
caddy start, migrations reach 0022, `/api/health` answers through Caddy, also with automatic
(internal) TLS.

1. **DNS and ports.** Point an A/AAAA record for your domain (for example `app.example.com`) at
   the VPS. Open TCP 80 and 443 (and UDP 443 for HTTP/3). Port 80 must be reachable for the
   certificate challenge.
2. **Install** Docker with the compose plugin; `git clone` the repository.
3. **Configure `.env`** (copy `.env.example`; never commit it):

   | Variable | VPS value |
   | --- | --- |
   | `SITE_ADDRESS` | the bare domain, for example `app.example.com`. Caddy then obtains and renews a Let's Encrypt certificate and redirects HTTP to HTTPS. Empty means plain HTTP on :80. |
   | `PUBLIC_APP_URL` | `https://app.example.com` (Stripe return URLs and reminder links) |
   | `CORS_ORIGINS` | `https://app.example.com` (explicit origins only, `*` is refused; credentials off) |
   | `DATABASE_URL` | keep `postgresql+asyncpg://pcn:pcn@db:5432/pcn` (db is not published). Change the password in both `.env` and `docker-compose.yml` if the database is ever reachable from outside. |
   | `ANTHROPIC_API_KEY` | your key; empty means fallback-only role-play |
   | `STRIPE_SECRET_KEY` | Stripe TEST key `sk_test_...` |
   | `STRIPE_WEBHOOK_SECRET` | the `whsec_...` of the endpoint you register below |
   | `DEMO_CONTROLS` | `true` on the hackathon deploy (enables `/api/demo/*`); `false` for anything real |
   | `DOCS_ENABLED` | `true` serves `/api/docs`; `false` hides it |
   | Rate limits | `ROLEPLAY_TURNS_PER_HOUR=40`, `SESSION_CREATIONS_PER_MINUTE=20`, `EVENTS_REQUESTS_PER_MINUTE=120`, `PUBLIC_CARD_REQUESTS_PER_MINUTE=30` |

   Other settings (`COACH_*`, `LLM_TIMEOUT_SECONDS`, `EVAL_JUDGE_MODEL`) are documented in
   `.env.example`. Session creation is limited per client address: judges behind one office NAT
   share the 20 per minute.
4. **Stripe ids.** On any machine with the test key, run `uv run python -m scripts.stripe_setup`
   (see [Run locally](#run-locally)) and deploy the updated `content/pricing.json`.
5. **Start** (use the base file only; the dev override would publish the database on 55432):

   ```bash
   docker compose -f docker-compose.yml up --build -d
   docker compose -f docker-compose.yml ps          # db and api healthy
   curl -s https://app.example.com/api/health
   ```

   The api container runs `alembic upgrade head` on every start.
6. **Register the webhook** in the Stripe dashboard (test mode): Developers, Webhooks, Add
   endpoint, URL `https://app.example.com/api/webhooks/stripe`, events:
   `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`,
   `customer.subscription.updated`, `customer.subscription.deleted`,
   `test_helpers.test_clock.ready`. Copy the signing secret into `STRIPE_WEBHOOK_SECRET` and
   restart the api: `docker compose -f docker-compose.yml up -d api`.
7. **Run the [Stripe checklist](#manual-stripe-test-mode-run-pending-user-action)** against the
   deployed URL.

**Constraints and notes**

- **Exactly one api worker.** The rate limiters are in memory; the Dockerfile starts uvicorn with
  `--workers 1`. Do not scale `api` or raise workers until the limiter moves to shared storage.
- The rate-limit key is the last `X-Forwarded-For` hop, which relies on Caddy overwriting that
  header. Do not expose the api port around Caddy.
- Caddy adds HSTS (effective only with the real domain and TLS), `nosniff`, `no-referrer`,
  `X-Frame-Options: DENY`, and a 64 KB body limit on `/api/*` (the app also returns 413).
- The container runs as an unprivileged user (uid 10001). `content/` is mounted read-only.
- `caddy_data` holds the certificates: keep the volume across restarts to avoid certificate
  rate limits.
- Logs never contain role-play text or card ids, but they do carry request ids, paths (card ids
  redacted), and timing.

## Manual Stripe test-mode run (pending user action)

Not yet run against real Stripe. Needs a Stripe TEST key, `scripts.stripe_setup` done, and the
webhook endpoint registered (or `stripe listen` locally). Use the app through the frontend or
the `/api/docs` page with an `X-Session-Token`.

1. Create a session, finish the quiz, `POST /api/billing/checkout` with `autoRenewConsent: true`
   and open the returned Checkout URL.
2. Pay with card `4242 4242 4242 4242`, any future expiry and CVC. Expect the webhooks
   `checkout.session.completed` and `invoice.paid`; `GET /api/billing/subscription` shows
   `active`; the lesson schedule exists and Q3/Q5 raw answers are gone.
3. `POST /api/demo/jump-to-renewal`. On the Stripe path this advances the Stripe **Test Clock**;
   expect `test_helpers.test_clock.ready` then `invoice.paid` for the renewal and
   `renewalCount` increases to 1. Check Stripe Dashboard, Billing, Test clocks.
4. Failing card: with a fresh session call `POST /api/demo/fail-next-payment` before the jump,
   then jump to renewal. Expect `invoice.payment_failed`, status `past_due`, and gated endpoints
   answering `402` with `reason: "past_due"`.
5. Also check: cancel (`POST /api/billing/cancel`) gives `canceling`; the checkout cancel URL
   lands on the frontend with "No payment was made"; replaying a webhook event changes nothing.

**Untested against real Stripe:** `attach_failing_payment_method` also sets the failing method as the
default payment method on the existing subscription (so the renewal really fails). That override
has only been tested with a fake. If step 4 does not produce `past_due`, this is the first place
to look. `past_due` cannot be cancelled normally (illegal transition); gentle exit is the way out.

Record the result in `context/PROGRESS.md`.

## Evals (NOT YET RUN)

> **Status: NOT RUN.** No real-model evaluation has been executed (no API key, no spend, no human
> judge labels). Do not treat any quality claim about the coach as verified. See
> [`docs/decisions/llm-harness.md`](docs/decisions/llm-harness.md) for the selection rule, the plan
> and the exact commands.

The eval runner (`backend/evals/`) calls the production coach adapter and the domain rules. **Real
runs cost money. Ask the owner first. Always run `--dry-run` first**; it prints the call count and
the worst-case cost and calls no model.

```bash
cd backend
uv run python -m evals.run --validate-only                       # dataset check, no model call
uv run python -m evals.run --config production --set dev --dry-run   # estimate only
# Real runs (each asks for confirmation; they are NOT RUN yet):
uv run python -m evals.run --stage prompt --set dev              # prompt v1 vs v2
uv run python -m evals.run --stage model-effort --set dev --prompt-version 2
uv run python -m evals.run --stage harness --set dev --prompt-version 2
```

Judge calibration needs human labels first (a person, never a model: see
`backend/evals/LABELING.md`), then `uv run python -m evals.calibrate`; `--judge` is refused until a
calibration report passes.

**Pre-demo gate (after any prompt, model or SDK change, and before every demo):**
`cd backend && uv run python -m evals.run --config production --set test` (costs money), and record
the result in `context/PROGRESS.md`. This gate cannot pass meaningfully until the harness selection
has run.

## Where to change content

Everything the learner reads, and every rule and number, is data in `content/` (see
`content/README.md`). Adding a lesson needs no Python.

| Change | File |
| --- | --- |
| Quiz questions, tags, "what we heard" | `content/quiz.json` |
| Plan rules, modules, pace (lessons per week) | `content/plan-rules.json` |
| Funnel, Today, paywall and gentle-exit copy | `content/funnel-copy.json` |
| Prices, plan lengths, Stripe ids | `content/pricing.json` |
| Phrase bank | `content/phrases.json` |
| Lessons | `content/lessons/m1_l1.json` to `m1_l5.json` |
| Role-play prompts (versioned, never edit a version that has an eval report) | `content/prompts/roleplay-turn.v<N>.md` |
| Safety terms, medical terms, fixed coach tips | `content/safety-terms.json` |
| Crisis resources | `content/crisis-resources.json` |
| Visit-sheet questions | `content/visit-questions.json` |
| Eval cases | `backend/evals/datasets/golden.jsonl` (source package: `content/evals/roleplay-evals.json`) |

The app validates all content at startup and refuses to start on an invalid file (the error names
the file and field). Content edits never reshuffle an already built plan.

## API overview

Interactive docs: **`/api/docs`** (OpenAPI at `/api/openapi.json`, controlled by `DOCS_ENABLED`).
All routes are under `/api`, JSON, camelCase. Session auth: header `X-Session-Token` (returned by
`POST /api/session`). Groups: session, quiz, plan (funnel preview and gift), pricing and billing,
Stripe webhook, app (plan, today, lessons, role-play, check-ins, skills, profile, phrases, care
card, visit sheet; need a subscription), exit (gentle exit), public (care card, crisis resources,
health), demo controls (`DEMO_CONTROLS`), events. Errors: `{"error": {"code", "message",
"details"}}`; frontend-relevant codes: `402` gate with reason (`no_plan`, `no_subscription`,
`past_due`, `ended`), `409` quiz locked, `423` lesson locked (`unlockOn`), `429` rate limit,
`410` revoked card, `413` body over 64 KB.

Funnel and activation metrics for the pitch: `psql "$DATABASE_URL" -f backend/scripts/metrics.sql`.

## Before launch checklist

For the user and the content owner. None of this is done by the code.

- [ ] Run the [manual Stripe test-mode checklist](#manual-stripe-test-mode-run-pending-user-action)
      and the VPS deploy; register the webhook with the six event types.
- [ ] Run the real-model evals, or consciously accept the unmeasured default
      (`docs/decisions/llm-harness.md`). Get the owner's budget approval first.
- [ ] **Verify crisis numbers** in `content/crisis-resources.json` (all flagged
      `verifyBeforeLaunch`; Adult Protective Services uses the Eldercare Locator 1-800-677-1116,
      since there is no single national APS number) and record who verified them and when.
- [ ] **Verify the grief-support URL** in the gentle-exit copy (`content/funnel-copy.json`,
      `gentleExit`): `https://hospicefoundation.org/Grief-Support` was written from memory. Also
      confirm 1-800-272-3900 and 988.
- [ ] **Content-owner review** of lessons `m1_l2` to `m1_l5` (drafts: wording, parent lines,
      fallbacks, day-2 notes, doctor notes, recap, the 29 lesson eval cases marked
      `needsContentReview`) and of the `gentleExit` copy.
- [ ] **Safety-terms review** of `content/safety-terms.json`, including the medical-terms list
      (20 terms drafted by the build agent) and the fixed coach tips; the eval data
      `backend/evals/data/shaming-words.json` (21 terms).
- [ ] Replace placeholder prices in `content/pricing.json` (demo prices, "TBD by test") and run
      `scripts.stripe_setup` again.
- [ ] Change the privacy copy to "Saved privately to this session. No account, no name needed."
- [ ] Frontend route assumptions: `/checkout/return?checkout_id=...` and
      `/paywall?checkout=canceled` (Stripe return URLs), `/card/{id}` (public care card) and
      `/lessons/{id}` (reminder link). These were guesses; fix `PUBLIC_APP_URL` usage if the
      frontend differs.
- [ ] Confirm the eval composite definition (mean of per-goal accuracy, exact-score rate, argued
      accuracy, flag F1) and verify the model/price assumptions listed in
      `docs/decisions/llm-harness.md`.
- [ ] Decide on `FALLBACK_MODELS` (server-side refusal fallback for `claude-opus-5-5` was the agent's
      assumption: verify against the API docs).
- [ ] Set `DEMO_CONTROLS=false` for anything that is not a demo.

## Known limitations

- **Rate limiters are in memory** (per process): one api worker only; limits reset on restart.
- **No accounts.** Losing the session token (clearing browser data, another device) loses access.
- `content/phrases.json` has only **4 `general` phrases**; the gift sheet needs 5 (persona A has no
  Q5), so the builder fills from other phrases in list order. Add a fifth general phrase.
- `extraForFacility` in `m1_l1` is **not rendered** (the lesson read lacks the living-situation
  tag). Wire it or drop it.
- `m1_l1` has only **2 fallback scenarios for 3 rounds**.
- New screen type **`phrases_review`** (in `m1_l5`): the frontend must render it
  (`title`, `intro`, `emptyText`, plus `phrases` supplied by the API).
- Lessons `m1_l2` to `m1_l5` are drafts pending content-owner review.
- The role-play prompt v1 adapter sends its input as XML tags while the v1 file describes JSON, so
  a fixed `INPUT_FORMAT_NOTE` is part of the effective prompt v1 (record it in eval reports).
- Metrics: day-0 and week-1 use the UTC date of app time; client events may double count
  server-side event names (metrics read lessons, role-play and subscriptions from tables).
- `--batch` (Batches API) in the eval runner is not implemented.
- Frontend: not built yet.
