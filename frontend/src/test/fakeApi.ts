/**
 * In-memory fake of the funnel endpoints, installed over `fetch`. Shared by every funnel test.
 *
 * It honours the backend contract: 401 for an unknown token, 409 `quiz_locked` after subscribing,
 * 402 reasons, 422 `quiz_incomplete`, 429 on demand. It does NOT build plans: it serves the
 * persona fixtures captured from the real backend (the persona is picked from Q3).
 */
import { vi } from "vitest";
import answerFixture from "./fixtures/answer.json";
import completeFixture from "./fixtures/complete.json";
import errors from "./fixtures/errors.json";
import eventsFixture from "./fixtures/events.json";
import funnelCopyFixture from "./fixtures/funnel-copy.json";
import giftA from "./fixtures/gift-a.json";
import giftB from "./fixtures/gift-b.json";
import giftC from "./fixtures/gift-c.json";
import planGated from "./fixtures/plan-gated.json";
import previewA from "./fixtures/preview-a.json";
import previewB from "./fixtures/preview-b.json";
import previewC from "./fixtures/preview-c.json";
import pricingFixture from "./fixtures/pricing.json";
import quizFixture from "./fixtures/quiz.json";
import subscriptionDemo from "./fixtures/subscription-demo.json";
import type { AccessReason } from "../api/errors";
import { gateFake } from "./fakeApp/core";
import { type AppScenario, DEFAULT_APP_SCENARIO, type FakeRes, serveFakeAreas } from "./fakeApp/registry";

export type Persona = "a" | "b" | "c";

const PERSONAS = {
  a: { preview: previewA, gift: giftA, branch: "noticing" },
  b: { preview: previewB, gift: giftB, branch: "recent" },
  c: { preview: previewC, gift: giftC, branch: "changing" },
} as const;

const Q3_TO_PERSONA: Record<string, Persona> = {
  noticing: "a",
  recent: "b",
  changing: "c",
  hospital: "c",
};

/** Questions that must be answered before `complete` (q5 is skippable, reassure_* are screens). */
const REQUIRED = quizFixture.questions
  .filter((q) => q.type !== "interstitial" && q.id !== "q5_changes")
  .map((q) => q.id);

export const FAKE_CHECKOUT_URL = "https://checkout.stripe.com/c/pay/cs_test_fake";
export const FAKE_CHECKOUT_ID = "cs_test_fake";

export interface Injected {
  method: string;
  /** Matched against the path after `/api`, exact or prefix when it ends with `*`. */
  path: string;
  status: number;
  body: unknown;
  /** Consumed after this many matches (default: once). */
  times: number;
}

export interface FakeScenario extends AppScenario {
  /** POST /session answers 429 rate_limited. */
  sessionRateLimited: boolean;
  /** POST /events answers 429 rate_limited. */
  eventsRateLimited: boolean;
  /** Stripe is configured: checkout works. Default false (502 with the demo hint, like the real default). */
  stripeConfigured: boolean;
  /** GET /billing/checkout/:id reports paid (and subscribes the session). */
  checkoutPaid: boolean;
  /** Subscription state served by the gate probe when subscribed. */
  accessReason: AccessReason | null;
  /** The next fetch rejects like a dropped connection. */
  networkDown: boolean;
}

export interface SessionState {
  answers: Record<string, unknown>;
  lastQuestionId: string | null;
  completed: boolean;
  subscribed: boolean;
  /** Scratch space of the app fakes (`src/test/fakeApp`). */
  app: Record<string, unknown>;
}

export interface FakeApi {
  scenario: FakeScenario;
  /** Every request made: method, path (after /api) and the token header. Bodies are not kept. */
  calls: { method: string; path: string; token: string | null }[];
  sessions: Map<string, SessionState>;
  /** Make a matching request answer with this status and body (once by default). */
  inject: (rule: Omit<Injected, "times"> & { times?: number }) => void;
  /** Convenience: an API error in the shared shape. */
  injectError: (
    method: string,
    path: string,
    status: number,
    code: string,
    details?: Record<string, unknown>,
  ) => void;
  restore: () => void;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function toResponse(res: FakeRes): Response {
  return res.status === 204 ? new Response(null, { status: 204 }) : json(res.status, res.body);
}

const apiError = (status: number, code: string, message: string, details = {}): Response =>
  json(status, { error: { code, message, details } });

function parseBody(init: RequestInit | undefined): Record<string, unknown> {
  if (typeof init?.body !== "string") return {};
  try {
    const parsed: unknown = JSON.parse(init.body);
    return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function personaOf(state: SessionState): Persona {
  const q3 = state.answers["q3_situation"];
  return (typeof q3 === "string" ? Q3_TO_PERSONA[q3] : undefined) ?? "a";
}

function missingIds(state: SessionState): string[] {
  return REQUIRED.filter((id) => state.answers[id] === undefined);
}

export function installFakeApi(initial: Partial<FakeScenario> = {}): FakeApi {
  const scenario: FakeScenario = {
    sessionRateLimited: false,
    eventsRateLimited: false,
    stripeConfigured: false,
    checkoutPaid: true,
    accessReason: null,
    networkDown: false,
    ...DEFAULT_APP_SCENARIO,
    ...initial,
  };
  const sessions = new Map<string, SessionState>();
  const injected: Injected[] = [];
  const calls: FakeApi["calls"] = [];
  let counter = 0;

  const matchInjected = (method: string, path: string): Injected | undefined =>
    injected.find(
      (r) =>
        r.times > 0 &&
        r.method === method &&
        (r.path.endsWith("*") ? path.startsWith(r.path.slice(0, -1)) : r.path === path),
    );

  const handle = (method: string, path: string, token: string | null, body: Record<string, unknown>): Response => {
    if (method === "POST" && path === "/session") {
      if (scenario.sessionRateLimited) {
        return apiError(429, "rate_limited", "Too many requests. Please try again in a minute.");
      }
      counter += 1;
      const created = `fake-token-${counter}`;
      sessions.set(created, {
        answers: {},
        lastQuestionId: null,
        completed: false,
        subscribed: false,
        app: {},
      });
      return json(201, { token: created, timezone: "America/New_York" });
    }

    const state = token ? sessions.get(token) : undefined;
    if (method === "GET" && path === "/pricing") {
      if (state) return json(200, pricingFixture);
      return json(200, {
        ...pricingFixture,
        plans: pricingFixture.plans.map((p) => ({ ...p, firstRenewalDate: null })),
      });
    }
    if (method === "GET" && path.startsWith("/cards/")) {
      // The public care card: no token, no session.
      const served = serveFakeAreas(appRequest(method, path, token, body, undefined));
      if (served) return toResponse(served);
    }
    if (!state) return json(401, errors["401"]);

    if (method === "GET" && path === "/quiz") {
      return json(200, {
        questions: quizFixture.questions,
        answers: state.answers,
        branch: branchOf(state),
        lastQuestionId: state.lastQuestionId,
        completed: state.completed,
        locked: state.subscribed,
      });
    }
    if (method === "PUT" && path.startsWith("/quiz/answers/")) {
      const id = decodeURIComponent(path.slice("/quiz/answers/".length));
      if (state.subscribed) return json(409, errors.quizLocked409);
      const known = quizFixture.questions.some((q) => q.id === id && q.type !== "interstitial");
      if (!known) return apiError(422, "invalid_answer", "That answer is not valid.");
      if (body["value"] === null || body["value"] === undefined) {
        state.answers = Object.fromEntries(Object.entries(state.answers).filter(([k]) => k !== id));
      } else state.answers[id] = body["value"];
      state.lastQuestionId = id;
      return json(200, { ...answerFixture, questionId: id, branch: branchOf(state), lastQuestionId: id });
    }
    if (method === "POST" && path === "/quiz/complete") {
      if (state.subscribed) return json(409, errors.quizLocked409);
      const missing = missingIds(state);
      if (missing.length > 0) {
        return apiError(422, "quiz_incomplete", "Some questions still need an answer.", {
          questionIds: missing,
        });
      }
      state.completed = true;
      return json(200, completeFixture);
    }
    if (method === "GET" && (path === "/plan/preview" || path === "/plan/gift")) {
      if (!state.completed) return json(402, errors.noPlan402);
      const persona = PERSONAS[personaOf(state)];
      return json(200, path === "/plan/preview" ? persona.preview : persona.gift);
    }
    if (method === "GET" && path === "/funnel-copy") return json(200, funnelCopyFixture);
    if (method === "GET" && path === "/plan") {
      if (!state.completed) return json(402, errors.noPlan402);
      if (!state.subscribed) return json(402, errors.noSubscription402);
      if (scenario.accessReason) {
        return apiError(402, "payment_required", "Your access needs attention.", {
          reason: scenario.accessReason,
        });
      }
      return json(200, planGated);
    }
    if (method === "POST" && path === "/billing/demo") return subscribe(state, body, "demo");
    if (method === "POST" && path === "/billing/checkout") {
      if (!scenario.stripeConfigured) return json(502, errors.gateway502);
      if (state.subscribed) return json(409, errors.alreadySubscribed409);
      if (body["autoRenewConsent"] !== true) return json(422, errors.consentRequired422);
      return json(200, { checkoutId: FAKE_CHECKOUT_ID, url: FAKE_CHECKOUT_URL });
    }
    if (method === "GET" && path.startsWith("/billing/checkout/")) {
      if (!scenario.stripeConfigured) return json(502, errors.gateway502);
      if (scenario.checkoutPaid) state.subscribed = true;
      return json(200, {
        paid: scenario.checkoutPaid,
        message: scenario.checkoutPaid ? null : "No payment has been received for this checkout.",
        subscription: scenario.checkoutPaid
          ? { ...subscriptionDemo, status: "active", source: "stripe" }
          : { ...subscriptionDemo, status: "none", planId: null, source: null },
      });
    }
    if (method === "POST" && path === "/events") {
      if (scenario.eventsRateLimited) return apiError(429, "rate_limited", "Too many requests.");
      const events = Array.isArray(body["events"]) ? body["events"] : [];
      return json(200, { ...eventsFixture, stored: events.length });
    }
    const req = appRequest(method, path, token, body, {
      completed: state.completed,
      subscribed: state.subscribed,
      app: state.app,
      destroy: () => sessions.delete(token ?? ""),
    });
    const served = gateFake(req) ?? serveFakeAreas(req);
    if (served) return toResponse(served);
    return apiError(404, "not_found", "Not found.");
  };

  const appRequest = (
    method: string,
    path: string,
    token: string | null,
    body: Record<string, unknown>,
    session: Parameters<typeof serveFakeAreas>[0]["session"],
  ): Parameters<typeof serveFakeAreas>[0] => ({ method, path, token, body, scenario, session });

  function branchOf(state: SessionState): string | null {
    return state.answers["q3_situation"] === undefined ? null : PERSONAS[personaOf(state)].branch;
  }

  function subscribe(state: SessionState, body: Record<string, unknown>, source: "demo"): Response {
    if (!state.completed) return json(402, errors.noPlan402);
    if (state.subscribed) return json(409, errors.alreadySubscribed409);
    if (body["autoRenewConsent"] !== true) return json(422, errors.consentRequired422);
    state.subscribed = true;
    return json(200, { ...subscriptionDemo, source });
  }

  const fetchFake = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    if (scenario.networkDown) return Promise.reject(new TypeError("Failed to fetch"));
    const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
    const path = url.replace(/^\/api/, "").split("?")[0] ?? "";
    const method = (init?.method ?? "GET").toUpperCase();
    const headers = new Headers(init?.headers);
    const token = headers.get("X-Session-Token");
    calls.push({ method, path, token });
    const rule = matchInjected(method, path);
    if (rule) {
      rule.times -= 1;
      return Promise.resolve(json(rule.status, rule.body));
    }
    return Promise.resolve(handle(method, path, token, parseBody(init)));
  };

  vi.stubGlobal("fetch", vi.fn(fetchFake));

  return {
    scenario,
    calls,
    sessions,
    inject: (rule) => injected.push({ times: 1, ...rule }),
    injectError(method, path, status, code, details = {}) {
      injected.push({
        method,
        path,
        status,
        times: 1,
        body: { error: { code, message: "Injected failure.", details } },
      });
    },
    restore: () => vi.unstubAllGlobals(),
  };
}
