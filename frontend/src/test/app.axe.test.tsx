/**
 * G18: an axe pass over every registered screen state of the app, through the real route table and the
 * fake API. Each row names the state, how to put the fake in it, where to go and which heading means
 * "ready" (a loading screen can share roles with the ready screen, so the wait is on a heading).
 */
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../api/session";
import { routes } from "../router";
import { type FakeApi, type SessionState, installFakeApi } from "./fakeApi";
import { appFixture } from "./fakeApp/fixtures";
import type { AppScenario } from "./fakeApp/registry";
import "./fakeApp/core";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => void data.delete(k),
    setItem: (k, v) => void data.set(k, v),
  };
}

let api: FakeApi;
let session: SessionState;
let view: ReturnType<typeof render> | undefined;

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  clearToken();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  vi.spyOn(console, "error").mockImplementation(() => undefined); // jsdom canvas noise from axe
  api = installFakeApi();
  session = { answers: {}, lastQuestionId: null, completed: true, subscribed: true, app: {} };
  api.sessions.set("fake-token-axe", session);
  setToken("fake-token-axe");
});
afterEach(() => {
  view?.unmount();
  view = undefined;
  api.restore();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const ph = (id: string, text: string) => ({ id, text, source: "scenario", lessonId: "m1_l1", savedAt: "2026-01-05T09:00:00Z" });
const card = (status: string) => {
  session.app["phrases"] = [ph("p1", "No rush. Take my arm?")];
  session.app["card"] = { status, ids: status === "not_published" ? [] : ["p1"], published: 1 };
};

interface Row {
  name: string;
  path: string;
  /** What the page shows when it is ready: a heading (any level) or visible text. */
  ready: { heading: string | RegExp } | { text: string | RegExp };
  scenario?: Partial<AppScenario>;
  prep?: () => void;
  signedOut?: boolean;
}

const TODAY = { heading: /^Today with / };
const ROWS: Row[] = [
  // Today in every state the API can serve
  { name: "today fresh with the welcome card", path: "/today", ready: TODAY },
  { name: "today after lesson 1", path: "/today", ready: TODAY, scenario: { today: "after_lesson_1" } },
  { name: "today day 2 (check-in, practice round)", path: "/today", ready: TODAY, scenario: { today: "day2" } },
  { name: "today with the care card nudge", path: "/today", ready: TODAY, scenario: { today: "nudge" } },
  { name: "today all done", path: "/today", ready: TODAY, scenario: { today: "all_done" } },
  { name: "today without demo controls", path: "/today", ready: TODAY, scenario: { demoControls: false } },
  { name: "today past due notice", path: "/today", ready: { text: /update your card/i }, scenario: { subscription: "past_due" } },
  { name: "today load error", path: "/today", ready: { text: "Try again" }, prep: () => api.injectError("GET", "/today", 500, "internal_error", {}) },
  // lessons
  { name: "lesson setup question", path: "/lessons/m1_l1", ready: { heading: "When Mom asks again" } },
  { name: "lesson phrase book (m1_l5)", path: "/lessons/m1_l5", ready: { heading: /phrase book/i }, scenario: { today: "all_done" } },
  { name: "lesson locked (423)", path: "/lessons/m1_l2", ready: { heading: /isn.t open yet/ } },
  { name: "lesson not found (404)", path: "/lessons/nope", ready: { heading: /find this lesson/ } },
  { name: "practice round", path: "/today/practice", ready: { heading: "2-minute practice" }, scenario: { today: "day2" } },
  { name: "practice round when none is offered", path: "/today/practice", ready: { heading: "No practice right now" } },
  // plan
  { name: "plan path", path: "/plan", ready: { heading: /course/i } },
  // profile
  { name: "profile empty", path: "/profile", ready: { heading: /page/i } },
  { name: "profile filled", path: "/profile", ready: { heading: /page/i }, prep: () => (session.app["profile"] = appFixture("profile-filled")) },
  // care card
  { name: "care card not shared", path: "/care-card", ready: { heading: /care card/i } },
  { name: "care card shared", path: "/care-card", ready: { heading: /care card/i }, prep: () => card("published") },
  { name: "care card update available", path: "/care-card", ready: { heading: /care card/i }, prep: () => card("update_available") },
  { name: "care card stopped", path: "/care-card", ready: { heading: /care card/i }, prep: () => card("revoked") },
  // visit sheet
  { name: "visit sheet empty", path: "/visit-sheet", ready: { heading: /next doctor visit/i } },
  { name: "visit sheet filled", path: "/visit-sheet", ready: { heading: /next doctor visit/i }, prep: () => (session.app["visitSheet"] = appFixture("visit-sheet-filled")) },
  // skills
  { name: "skills fresh", path: "/skills", ready: { heading: "Your skills" } },
  { name: "skills after a run", path: "/skills", ready: { heading: "Communication" }, prep: () => (session.app["ranRoleplay"] = true) },
  { name: "skills full", path: "/skills", ready: { heading: "Communication" }, prep: () => api.inject({ method: "GET", path: "/skills", status: 200, body: appFixture("skills-full") }) },
  // settings and exits
  { name: "settings (demo)", path: "/settings", ready: { heading: "Manage my plan" } },
  { name: "settings (active)", path: "/settings", ready: { heading: "Manage my plan" }, scenario: { subscription: "active" } },
  { name: "settings (canceling)", path: "/settings", ready: { heading: "Manage my plan" }, scenario: { subscription: "canceling" } },
  { name: "settings (past due)", path: "/settings", ready: { heading: "Manage my plan" }, scenario: { subscription: "past_due" } },
  { name: "settings (ended)", path: "/settings", ready: { heading: "Manage my plan" }, scenario: { subscription: "ended" } },
  { name: "cancel step", path: "/settings/cancel", ready: { text: "Keep my plan" } },
  { name: "gentle exit step 1", path: "/settings/gentle-exit", ready: { text: "Continue" } },
  // outside the shell
  { name: "public card", path: "/card/abc", ready: { heading: /^What works with/ }, signedOut: true },
  { name: "public card revoked", path: "/card/abc", ready: { heading: "This card is no longer shared" }, scenario: { publicCard: "revoked" }, signedOut: true },
  { name: "public card missing", path: "/card/abc", ready: { heading: "We can't find this card" }, scenario: { publicCard: "missing" }, signedOut: true },
  { name: "public card rate limited", path: "/card/abc", ready: { heading: "Too many people opened this link" }, scenario: { publicCard: "rate_limited" }, signedOut: true },
  { name: "not found", path: "/nope", ready: { heading: /find that page/ }, signedOut: true },
];

describe("axe sweep of every app state", () => {
  it.each(ROWS.map((r) => [r.name, r] as const))("%s", async (_name, row) => {
    Object.assign(api.scenario, row.scenario ?? {});
    row.prep?.();
    if (row.signedOut) clearToken();
    const router = createMemoryRouter(routes, { initialEntries: [row.path] });
    view = render(<RouterProvider router={router} />);
    if ("heading" in row.ready) await screen.findByRole("heading", { name: row.ready.heading });
    else await screen.findAllByText(row.ready.text);
    expect(await axe(document.body)).toHaveNoViolations();
    expect(document.body.textContent).not.toMatch(/\{[A-Za-z]+\}/);
    // Honest selling: no price per day, fake urgency or retention offers on any screen the API fills.
    expect(document.body.textContent).not.toMatch(
      /per day|\/ ?day\b|limited[- ]time|hurry|countdown|expires in|spots? left|special offer|don't go|we.ll miss you/i,
    );
  });

  it("the desktop shell (sidebar) is clean too", async () => {
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: query.includes("min-width: 1024px"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      onchange: null,
      dispatchEvent: () => false,
    }));
    for (const path of ["/today", "/plan", "/settings"]) {
      const router = createMemoryRouter(routes, { initialEntries: [path] });
      view = render(<RouterProvider router={router} />);
      await screen.findByRole("heading", { level: 1 });
      expect(await axe(document.body)).toHaveNoViolations();
      // One primary navigation ("App"): the sidebar from 1024px, never the tab bar as well.
      expect(screen.getAllByRole("navigation", { name: "App" })).toHaveLength(1);
      view.unmount();
    }
  });
});
