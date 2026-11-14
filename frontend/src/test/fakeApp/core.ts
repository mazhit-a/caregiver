/**
 * Baseline fake of every app endpoint, served from the fixtures captured from the real backend.
 * Stateful where a screen needs it (phrases, profile, visit sheet, care card, role-play runs,
 * lesson variant and step, subscription); the rest is a fixture. Areas refine it with their own
 * `registerFakeArea` (a later registration wins).
 */
import type { FakeApi } from "../fakeApi";
import errors from "../fixtures/errors.json";
import { appFixture } from "./fixtures";
import {
  type FakeAppSession,
  type FakeReq,
  type FakeRes,
  type RoleplayMode,
  type TodayState,
  registerFakeArea,
  route,
} from "./registry";

type Json = Record<string, unknown>;

const ok = (body: unknown): FakeRes => ({ status: 200, body });
const fail = (status: number, name: string): FakeRes => ({ status, body: appFixture(name) });
const error = (status: number, code: string, message: string, details: Json = {}): FakeRes => ({
  status,
  body: { error: { code, message, details } },
});

const GATED = [
  /^\/today$/, /^\/lessons\//, /^\/roleplay\//, /^\/phrases/, /^\/checkins$/, /^\/skills$/,
  /^\/profile$/, /^\/care-card$/, /^\/visit-sheet$/,
];

const PHRASE_STATE = "phrases";

function bag<T>(session: FakeAppSession, key: string, init: () => T): T {
  if (!(key in session.app)) session.app[key] = init();
  return session.app[key] as T;
}

/** 402 by the same rules as the real gate: no plan, no subscription, or the scenario's reason.
 *  `installFakeApi` calls it before any area, so an area cannot bypass the gate. */
export function gateFake(req: FakeReq): FakeRes | undefined {
  if (!GATED.some((re) => re.test(req.path)) || !req.session) return undefined;
  if (!req.session.completed) return { status: 402, body: errors.noPlan402 };
  if (!req.session.subscribed) return { status: 402, body: errors.noSubscription402 };
  const reason =
    req.scenario.accessReason ?? (req.scenario.subscription === "past_due" ? "past_due" : null);
  if (reason) {
    return error(402, "payment_required", "Your access needs attention. Please update your card.", {
      reason,
    });
  }
  return undefined;
}

// ---- lessons ------------------------------------------------------------------------------

const LESSON_FIXTURES: Record<string, (s: FakeAppSession) => string | null> = {
  m1_l1: (s) => {
    const variant = bag<string | null>(s, "variant", () => null);
    if (!variant) return "lesson-m1_l1-initial";
    return variant === "phone" ? "lesson-m1_l1-phone-main" : `lesson-m1_l1-${variant}`;
  },
  m1_l2: () => "lesson-m1_l2",
  m1_l5: () => "lesson-m1_l5",
};

function lessonOpen(lessonId: string, today: TodayState): boolean {
  if (lessonId === "m1_l1") return true;
  if (lessonId === "m1_l2") return today === "day2" || today === "nudge" || today === "all_done";
  return today === "all_done";
}

function lessonResponse(req: FakeReq, lessonId: string): FakeRes {
  const session = req.session as FakeAppSession;
  const pick = LESSON_FIXTURES[lessonId];
  if (!pick) {
    return error(404, "unknown_lesson", "We could not find this lesson.", { lesson: lessonId });
  }
  if (!lessonOpen(lessonId, req.scenario.today)) {
    return fail(423, "err-423-lesson-locked");
  }
  const name = pick(session);
  if (!name) return fail(404, "err-404-lesson");
  const lesson = appFixture<Json & { progress: Json }>(name);
  const step = bag<Record<string, number>>(session, "steps", () => ({}))[lessonId];
  if (step !== undefined) lesson.progress = { ...lesson.progress, step };
  return ok(lesson);
}

interface Screen {
  id: string;
  type: string;
  options?: { id: string }[];
  answers?: { id: string }[];
  miniTask?: { options: { id: string }[] } | null;
}

function answerResponse(req: FakeReq, lessonId: string): FakeRes {
  const session = req.session as FakeAppSession;
  const lesson = lessonResponse(req, lessonId);
  if (lesson.status !== 200) return lesson;
  const screens = (lesson.body as { screens: Screen[] }).screens;
  const screen = screens.find((s) => s.id === req.body["screenId"]);
  const value = req.body["value"];
  const bad = (): FakeRes => fail(422, "err-422-lesson-answer");
  if (!screen) return bad();
  if (screen.type === "setup_question") {
    if (!screen.options?.some((o) => o.id === value)) return bad();
    session.app["variant"] = value;
    const answer = appFixture<Json & { result: Json }>("answer-setup-both");
    return ok({ ...answer, screenId: screen.id, result: { variant: value } });
  }
  if (screen.type === "scenario") {
    if (!screen.answers?.some((a) => a.id === value)) return bad();
    return ok({ ...appFixture<Json>(`answer-scenario-${String(value)}`), screenId: screen.id });
  }
  if (screen.type === "learn" && screen.miniTask) {
    if (!screen.miniTask.options.some((o) => o.id === value)) return bad();
    const answer = appFixture<Json & { result: Json }>("answer-minitask-main");
    return ok({ ...answer, screenId: screen.id, result: { ...answer.result, optionId: value } });
  }
  if (screen.type === "plan") {
    return ok({ ...appFixture<Json>("answer-plan"), screenId: screen.id });
  }
  if (screen.type === "wrap") return ok({ ...appFixture<Json>("answer-wrap"), screenId: screen.id });
  return bad();
}

// ---- role-play ----------------------------------------------------------------------------------

interface Run {
  context: string;
  round: number;
  total: number;
  fallback: boolean;
  scores: number[];
}

function runs(session: FakeAppSession): Record<string, Run> {
  return bag<Record<string, Run>>(session, "runs", () => ({}));
}

function nextMode(req: FakeReq, run: Run): RoleplayMode | "fallback" {
  const script = req.scenario.roleplayMode;
  const turnsSoFar = bag<{ n: number }>(req.session as FakeAppSession, "turnCounter", () => ({ n: 0 }));
  const mode = script[Math.min(turnsSoFar.n, script.length - 1)] ?? "ai";
  turnsSoFar.n += 1;
  return run.fallback ? "fallback" : mode;
}

function turnResponse(req: FakeReq, runId: string): FakeRes {
  const session = req.session as FakeAppSession;
  const run = runs(session)[runId];
  if (!run) return fail(404, "err-404-run");
  const reply = req.body["reply"];
  if (typeof reply !== "string" || reply.trim() === "" || reply.length > 500) {
    return fail(422, "err-422-roleplay-empty");
  }
  if (req.body["round"] !== run.round) {
    return error(422, "round_mismatch", "This is not the current round.", {
      expected: run.round,
      got: req.body["round"],
    });
  }
  const mode = nextMode(req, run);
  const names: Record<string, string> = {
    ai: "roleplay-turn-ai-1",
    medical: "roleplay-turn-medical-1",
    fallback: "roleplay-turn-fallback-1",
    crisis: "roleplay-turn-crisis-1",
    emergency: "roleplay-turn-emergency-1",
  };
  const body = appFixture<Json>(names[mode] ?? "roleplay-turn-ai-1");
  if (mode === "fallback") run.fallback = true;
  const crisis = mode === "crisis";
  if (!crisis) run.round += 1;
  return ok({ ...body, round: req.body["round"], roundsTotal: run.total });
}

// ---- phrases, profile, card, sheet ----------------------------------------------------------------

interface PhraseRow {
  id: string;
  text: string;
  source: string;
  lessonId: string | null;
  savedAt: string;
}

function phrases(session: FakeAppSession): PhraseRow[] {
  return bag<PhraseRow[]>(session, PHRASE_STATE, () => []);
}

const PROFILE_KEYS = [
  "displayName", "enjoys", "calms", "avoid", "rhythm", "contacts", "caregiverFirstName",
];

function profileOf(session: FakeAppSession): Json {
  return bag<Json>(session, "profile", () => appFixture<Json>("profile-empty"));
}

function cardState(session: FakeAppSession): { status: string; ids: string[]; published: number } {
  return bag(session, "card", () => ({ status: "not_published", ids: [] as string[], published: 0 }));
}

function cardResponse(session: FakeAppSession): FakeRes {
  const card = cardState(session);
  const rows = phrases(session);
  const base = appFixture<Json>(
    card.status === "not_published"
      ? "care-card-not-published"
      : card.status === "revoked"
        ? "care-card-revoked"
        : card.status === "update_available"
          ? "care-card-update-available"
          : "care-card-published",
  );
  const available = rows.map((p) => ({ id: p.id, text: p.text }));
  return ok({
    ...base,
    chosenPhraseIds: card.ids,
    availablePhrases: card.status === "not_published" && rows.length === 0 ? base["availablePhrases"] : available,
  });
}

// ---- the routes ------------------------------------------------------------------------------------

const noDemo = (): FakeRes => error(404, "not_found", "Not found.");

function demoResponse(req: FakeReq, advance: boolean): FakeRes {
  if (!req.scenario.demoControls) return noDemo();
  if (advance && req.scenario.today === "after_lesson_1") req.scenario.today = "day2";
  return ok(appFixture(advance ? "demo-next-day" : "demo"));
}

function subscriptionBody(req: FakeReq, session: FakeAppSession): Json {
  const status = bag<{ value: string | null }>(session, "subscription", () => ({ value: null }));
  const current = status.value ?? req.scenario.subscription;
  const base = appFixture<Json>("subscription-demo");
  if (current === "demo") return base;
  const source = current === "none" ? null : "stripe";
  return { ...base, status: current, source, planId: current === "none" ? null : base["planId"] };
}

export const CORE_ROUTES = [
  route("GET", "/app-copy", (req) =>
    req.scenario.appCopy === "error"
      ? error(500, "internal_error", "Something went wrong.")
      : ok(appFixture("app-copy")),
  ),
  route("GET", "/today", (req) => {
    const names: Record<TodayState, string> = {
      fresh: "today-fresh",
      after_lesson_1: "today-after-l1",
      day2: "today-day2",
      nudge: "today-nudge",
      all_done: "today-all-done",
    };
    const today = appFixture<Json>(names[req.scenario.today]);
    if (!req.scenario.demoControls) {
      today["demo"] = null;
      today["order"] = (today["order"] as string[]).filter((s) => s !== "demo");
    }
    return ok(today);
  }),
  route("GET", /^\/lessons\/([^/]+)$/, (req, [id]) => lessonResponse(req, id ?? "")),
  route("POST", /^\/lessons\/([^/]+)\/answers$/, (req, [id]) => answerResponse(req, id ?? "")),
  route("POST", /^\/lessons\/([^/]+)\/complete$/, (req, [id]) => {
    const lesson = lessonResponse(req, id ?? "");
    if (lesson.status !== 200) return lesson;
    return ok(appFixture(id === "m1_l1" ? "complete" : "complete-last"));
  }),
  route("PUT", /^\/lessons\/([^/]+)\/progress$/, (req, [id]) => {
    const lesson = lessonResponse(req, id ?? "");
    if (lesson.status !== 200) return lesson;
    const step = req.body["step"];
    const count = (lesson.body as { screens: unknown[] }).screens.length;
    if (typeof step !== "number" || !Number.isInteger(step) || step < 0 || step >= count) {
      return fail(422, "err-422-progress");
    }
    bag<Record<string, number>>(req.session as FakeAppSession, "steps", () => ({}))[id ?? ""] = step;
    return ok({ ...appFixture<Json>("progress-put"), step });
  }),
  route("POST", "/roleplay/start", (req) => {
    const session = req.session as FakeAppSession;
    const practice = req.body["context"] === "practice_round";
    const start = appFixture<Json & { runId: string; roundsTotal: number }>(
      practice ? "roleplay-start-practice" : "roleplay-start-ai",
    );
    const runId = `00000000-0000-4000-8000-${String(Object.keys(runs(session)).length + 1).padStart(12, "0")}`;
    runs(session)[runId] = {
      context: practice ? "practice_round" : "lesson",
      round: 1,
      total: start.roundsTotal,
      fallback: false,
      scores: [],
    };
    return ok({ ...start, runId });
  }),
  route("POST", /^\/roleplay\/([^/]+)\/turn$/, (req, [id]) => turnResponse(req, id ?? "")),
  route("POST", /^\/roleplay\/([^/]+)\/finish$/, (req, [id]) => {
    const session = req.session as FakeAppSession;
    const run = runs(session)[id ?? ""];
    if (!run) return fail(404, "err-404-run");
    session.app["ranRoleplay"] = true;
    const name = run.fallback
      ? "roleplay-finish-fallback"
      : run.context === "practice_round"
        ? "roleplay-finish-practice"
        : "roleplay-finish-ai";
    return ok({ ...appFixture<Json>(name), runId: id });
  }),
  route("GET", "/phrases", (req) => ok({ phrases: phrases(req.session as FakeAppSession) })),
  route("POST", "/phrases", (req) => {
    const session = req.session as FakeAppSession;
    const text = req.body["text"];
    if (typeof text !== "string" || text.trim() === "") return fail(422, "err-422-phrase");
    const saved = appFixture<PhraseRow>("phrase-saved");
    const row: PhraseRow = {
      ...saved,
      id: `00000000-0000-4000-9000-${String(phrases(session).length + 1).padStart(12, "0")}`,
      text,
      source: String(req.body["source"] ?? saved.source),
      lessonId: typeof req.body["lessonId"] === "string" ? req.body["lessonId"] : null,
    };
    phrases(session).push(row);
    return { status: 201, body: row };
  }),
  route("DELETE", /^\/phrases\/([^/]+)$/, (req, [id]) => {
    const rows = phrases(req.session as FakeAppSession);
    const at = rows.findIndex((p) => p.id === id);
    if (at < 0) return fail(404, "err-404-phrase");
    rows.splice(at, 1);
    return { status: 204 };
  }),
  route("POST", "/checkins", (req) => {
    const session = req.session as FakeAppSession;
    if (bag<{ done: boolean }>(session, "checkin", () => ({ done: false })).done) {
      return fail(409, "err-409-checkin-again");
    }
    (session.app["checkin"] as { done: boolean }).done = true;
    return ok(appFixture(req.body["outcome"] === "didnt_help" ? "checkin-didnt-help" : "checkin-helped"));
  }),
  route("GET", "/skills", (req) =>
    ok(appFixture((req.session as FakeAppSession).app["ranRoleplay"] ? "skills-after-run" : "skills-fresh")),
  ),
  route("GET", "/profile", (req) => ok(profileOf(req.session as FakeAppSession))),
  route("PUT", "/profile", (req) => {
    const session = req.session as FakeAppSession;
    if (Object.keys(req.body).some((k) => !PROFILE_KEYS.includes(k))) return fail(422, "err-422-profile");
    const next = { ...profileOf(session), ...req.body, updatedAt: "2026-01-05T09:00:00Z" };
    session.app["profile"] = next;
    // Like the real policy: saving the profile again after publishing makes the card stale.
    const card = cardState(session);
    if (card.status === "published") card.status = "update_available";
    return ok(next);
  }),
  route("GET", "/care-card", (req) => cardResponse(req.session as FakeAppSession)),
  route("POST", "/care-card", (req) => {
    const card = cardState(req.session as FakeAppSession);
    if (card.status === "published" || card.status === "update_available") {
      return error(409, "card_already_published", "This card is already shared.");
    }
    card.status = "published";
    card.ids = Array.isArray(req.body["phraseIds"]) ? (req.body["phraseIds"] as string[]) : [];
    return cardResponse(req.session as FakeAppSession);
  }),
  route("PUT", "/care-card", (req) => {
    const card = cardState(req.session as FakeAppSession);
    if (card.status !== "published" && card.status !== "update_available") {
      return error(409, "card_not_published", "This card is not shared.");
    }
    card.status = "published";
    card.ids = Array.isArray(req.body["phraseIds"]) ? (req.body["phraseIds"] as string[]) : [];
    return cardResponse(req.session as FakeAppSession);
  }),
  route("DELETE", "/care-card", (req) => {
    cardState(req.session as FakeAppSession).status = "revoked";
    return cardResponse(req.session as FakeAppSession);
  }),
  // Public: no token needed (the session is undefined for it).
  route("GET", /^\/cards\/([^/]+)$/, (req) => {
    switch (req.scenario.publicCard) {
      case "revoked":
        return fail(410, "err-410-card");
      case "missing":
        return fail(404, "err-404-card");
      case "rate_limited":
        return error(429, "rate_limited", "Too many requests. Please try again in a minute.");
      default:
        return ok(appFixture("card-public"));
    }
  }),
  route("GET", "/visit-sheet", (req) =>
    ok(bag<Json>(req.session as FakeAppSession, "visitSheet", () => appFixture<Json>("visit-sheet-empty"))),
  ),
  route("PUT", "/visit-sheet", (req) => {
    const session = req.session as FakeAppSession;
    const questions = req.body["questions"];
    if (Array.isArray(questions) && questions.some((q) => typeof q === "object" && q !== null && "id" in q && q.id === "nope")) {
      return fail(422, "err-422-visit-sheet");
    }
    const current = bag<Json>(session, "visitSheet", () => appFixture<Json>("visit-sheet-empty"));
    const next: Json = { ...current, ...req.body, updatedAt: "2026-01-05T09:00:00Z" };
    if (Array.isArray(questions)) {
      next["questions"] = questions.map((q: { id?: string; text?: string }) => ({
        id: q.id ?? null,
        text: q.text ?? q.id ?? "",
        custom: q.id === undefined,
      }));
    }
    session.app["visitSheet"] = next;
    return ok(next);
  }),
  route("GET", "/billing/subscription", (req) => ok(subscriptionBody(req, req.session as FakeAppSession))),
  route("GET", "/billing/cancel-preview", (req) =>
    ok({
      ...appFixture<Json>("cancel-preview"),
      status: subscriptionBody(req, req.session as FakeAppSession)["status"],
    }),
  ),
  route("POST", "/billing/cancel", (req) => {
    const session = req.session as FakeAppSession;
    if (req.scenario.cancelFails) {
      return error(503, "billing_cancel_failed", "We couldn't cancel with the payment provider, so nothing changed.");
    }
    const current = subscriptionBody(req, session)["status"];
    if (current === "canceling" || current === "none" || current === "canceled" || current === "ended") {
      return fail(409, "err-409-cancel-again");
    }
    bag<{ value: string | null }>(session, "subscription", () => ({ value: null })).value = "canceling";
    return ok(appFixture("cancel"));
  }),
  route("POST", "/exit/gentle", (req) => {
    if (req.scenario.cancelFails) {
      return error(503, "billing_cancel_failed", "We couldn't cancel with the payment provider, so nothing was deleted.");
    }
    (req.session as FakeAppSession).destroy();
    return ok(appFixture("exit-gentle"));
  }),
  route("DELETE", "/session", (req) => {
    (req.session as FakeAppSession).destroy();
    return ok(appFixture("clear-data"));
  }),
  route("GET", "/demo", (req) => demoResponse(req, false)),
  route("POST", "/demo/next-day", (req) => demoResponse(req, true)),
  route("POST", "/demo/jump-to-renewal", (req) =>
    req.scenario.demoControls ? ok(appFixture("demo-jump-to-renewal")) : noDemo(),
  ),
  route("POST", "/demo/fail-next-payment", (req) =>
    req.scenario.demoControls ? fail(409, "demo-fail-next-payment") : noDemo(),
  ),
];

registerFakeArea("core", CORE_ROUTES);

/** Gives a session the plan and the subscription, as `POST /billing/demo` would. Returns its token. */
export function signIn(api: FakeApi, token = "fake-token-app"): string {
  api.sessions.set(token, {
    answers: {},
    lastQuestionId: null,
    completed: true,
    subscribed: true,
    app: {},
  });
  return token;
}
