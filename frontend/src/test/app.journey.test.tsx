/* eslint-disable @typescript-eslint/no-non-null-assertion -- fixture lookups in tests */
/**
 * G18: one scripted journey through the real route table and the fake API, from the paywall to the
 * gentle exit, plus privacy assertions and an axe pass over every registered screen state.
 * No sleeps: every step waits for a specific heading or text.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, getToken, setToken, TOKEN_KEY } from "../api/session";
import { routes } from "../router";
import { type FakeApi, installFakeApi } from "./fakeApi";
import { appFixture } from "./fakeApp/fixtures";
import { registerFakeArea, unregisterFakeArea } from "./fakeApp/registry";
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
const keysOf = (s: Storage): string[] => Array.from({ length: s.length }, (_, i) => s.key(i) ?? "");

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("read failed"));
    reader.readAsText(blob);
  });
}

type Json = Record<string, unknown>;
interface Sent {
  method: string;
  path: string;
  url: string;
  token: string | null;
  body: Json;
}

let api: FakeApi;
let logged: string[];
let sent: Sent[];
let router: ReturnType<typeof createMemoryRouter>;
let view: ReturnType<typeof render>;
let visited: string[];
let icsBlobs: Blob[];
const user = userEvent.setup({ delay: null });

/** Secrets typed during the journey: none of them may reach a URL, storage, console or a non-API request. */
const REPLIES = ["zebra-reply-one", "zebra-reply-two", "zebra-reply-three"];
const NOTE = "zebra-visit-note";
const PROFILE_NAME = "Walter";
let cardId = "";

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  clearToken();
  window.scrollTo = vi.fn();
  window.print = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  logged = [];
  for (const level of ["log", "info", "warn", "error", "debug"] as const) {
    vi.spyOn(console, level).mockImplementation((...args: unknown[]) => {
      logged.push(args.map(String).join(" "));
    });
  }
  api = installFakeApi({ stripeConfigured: true });
  const base = globalThis.fetch;
  sent = [];
  vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers);
    const url = String(input);
    sent.push({
      method: (init?.method ?? "GET").toUpperCase(),
      path: url.replace(/^\/api/, "").split("?")[0] ?? "",
      url,
      token: headers.get("X-Session-Token"),
      body: typeof init?.body === "string" ? (JSON.parse(init.body) as Json) : {},
    });
    return base(input, init);
  });
  icsBlobs = [];
  Object.assign(URL, {
    createObjectURL: vi.fn((blob: Blob) => {
      icsBlobs.push(blob);
      return "blob:ics";
    }),
    revokeObjectURL: vi.fn(),
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});
afterEach(() => {
  unregisterFakeArea("journey");
  view?.unmount();
  api.restore();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function renderAt(path: string) {
  router = createMemoryRouter(routes, { initialEntries: [path] });
  visited = [path];
  router.subscribe((s) => visited.push(s.location.pathname + s.location.search + s.location.hash));
  view = render(<RouterProvider router={router} />);
  return view;
}
const here = (): string => router.state.location.pathname;
const h1 = (name: string | RegExp) => screen.findByRole("heading", { level: 1, name });
const h2 = (name: string | RegExp) => screen.findByRole("heading", { level: 2, name });
const heading = (name: string | RegExp) => screen.findByRole("heading", { name });
const roleplayContinue = () =>
  waitFor(() => {
    const found = screen.getAllByRole("button", { name: "Continue" }).filter((b) => !b.hasAttribute("aria-disabled"));
    if (found.length !== 1) throw new Error("expected the role-play Continue button");
    return found[0] as HTMLElement;
  });
const nextBtn = () => {
  // The player's footer button (the role-play screen has its own "Continue" inside the screen).
  const found = screen.getAllByRole("button", { name: "Continue" }).filter((b) => b.hasAttribute("aria-disabled"));
  if (found.length !== 1) throw new Error("expected one player Continue button");
  return found[0] as HTMLElement;
}
const calls = (method: string, path: string | RegExp): Sent[] =>
  sent.filter((c) => c.method === method && (typeof path === "string" ? c.path === path : path.test(c.path)));

/** Mount the app again at the current path: only the token (localStorage) survives, like a reload. */
async function reload(expectHeading: string | RegExp, level = 1) {
  const path = router.state.location.pathname;
  view.unmount();
  renderAt(path);
  await screen.findByRole("heading", { level, name: expectHeading });
  expect(getToken()).not.toBeNull();
}

async function noAxeViolations(label: string) {
  const results = await axe(document.body);
  expect(results, label).toHaveNoViolations();
}

// ---- journey state of the fake -------------------------------------------------------------------

/**
 * Moves the fake's Today with the user's own actions, which the baseline fixture fake leaves to the
 * test: finishing lesson 1, simulated days, new phrases after a published card. The unlock rule is
 * `ceil(k*7/4)` days from the start for lesson k+1 (lesson 2 opens two days after lesson 1).
 */
function installJourneyArea() {
  const state = { days: 0, revoked: false };
  registerFakeArea("journey", [
    (req) => {
      if (req.method === "POST" && req.path === "/lessons/m1_l1/complete") {
        req.scenario.today = "after_lesson_1";
        return undefined;
      }
      if (req.method === "DELETE" && req.path === "/care-card") {
        state.revoked = true;
        return undefined;
      }
      if (req.method === "GET" && /^\/cards\//.test(req.path) && state.revoked) {
        return { status: 410, body: appFixture("err-410-card") };
      }
      if (req.method === "POST" && req.path === "/demo/next-day") {
        state.days += 1;
        req.scenario.today = "day2";
        return { status: 200, body: { ...appFixture<Json>("demo-next-day"), appToday: `2026-01-0${5 + state.days}` } };
      }
      if (req.method === "GET" && req.path === "/lessons/m1_l2") {
        if (state.days < 2) return { status: 423, body: appFixture("err-423-lesson-locked") };
        return undefined;
      }
      if (req.method === "GET" && req.path === "/plan") {
        const plan = appFixture<{ modules: { id: string; lessons: Json[] }[] } & Json>("plan");
        const lessons = plan.modules[0]!.lessons;
        lessons[0]!["status"] = req.scenario.today === "fresh" ? "available" : "done";
        lessons[1]!["status"] = state.days >= 2 ? "available" : "locked";
        return { status: 200, body: plan };
      }
      if (req.method === "GET" && req.path === "/today" && req.session) {
        const base = appFixture<Json>(
          { fresh: "today-fresh", after_lesson_1: "today-after-l1" }[req.scenario.today as string] ?? "today-day2",
        );
        const app = req.session.app;
        const rows = (app["phrases"] as unknown[] | undefined) ?? [];
        const card = app["card"] as { status: string; ids: string[] } | undefined;
        const order = (base["order"] as string[]).filter((s) => s !== "demo" || req.scenario.demoControls);
        if (state.days >= 2 && base["nextStep"]) {
          const step = base["nextStep"] as { lesson: Json };
          base["nextStep"] = {
            kind: "lesson",
            message: null,
            lesson: { ...step.lesson, status: "available" },
            unlockText: null,
          };
        }
        if (state.days >= 2) {
          base["checkIn"] = null;
          base["practiceRound"] = null;
          base["order"] = order.filter((s) => s !== "checkIn" && s !== "practiceRound");
        }
        if (card && card.status === "published" && rows.length > card.ids.length) {
          base["careCardNudge"] = {
            newPhraseCount: rows.length - card.ids.length,
            text: "Your care card has 1 new phrase. Update it?",
          };
          base["order"] = ["careCardNudge", ...(base["order"] as string[])];
        }
        return { status: 200, body: base };
      }
      return undefined;
    },
  ]);
  return state;
}

// ---- lesson steps ---------------------------------------------------------------------------------

async function openFirstLesson(variantLabel: string) {
  await user.click(await screen.findByRole("link", { name: "Start lesson" }));
  await h1("When Mom asks again");
  await user.click(await screen.findByRole("radio", { name: variantLabel }));
  await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "9"));
}

async function typedRoleplay() {
  await user.click(await screen.findByRole("button", { name: "Start practice" }));
  for (const [i, text] of REPLIES.entries()) {
    await user.type(await screen.findByRole("textbox", { name: "What would you say?" }), text);
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("AI-generated");
    await user.click(screen.getByRole("button", { name: i < 2 ? "Next round" : "See your practice" }));
  }
  await user.click(await roleplayContinue());
}

async function lessonOne(variant: "in_person" | "phone") {
  await openFirstLesson(variant === "phone" ? "On the phone" : "In person");
  expect(calls("POST", "/lessons/m1_l1/answers")[0]!.body).toEqual({ screenId: "s1_setup", value: variant });

  // scenario: pick the best reply and save the phrase
  await user.click(nextBtn());
  const replies = await screen.findAllByRole("radio");
  await user.click(replies[3]!); // the answer that follows all three steps, in both variants
  await user.click(await screen.findByRole("button", { name: "Save this phrase" }));
  await screen.findByRole("button", { name: "Saved" });
  await noAxeViolations("lesson scenario");

  // learn screens with the mini tasks (the reset task feeds the plan)
  await user.click(nextBtn());
  await user.click(await screen.findByRole("radio", { name: "Worry" }));
  await user.click(nextBtn());
  await screen.findByRole("radio", { name: /^You're wondering about it/ });
  // a reload here: only the token survives, the lesson resumes on this screen from the server's step
  await reload("When Mom asks again");
  await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "4"));
  await user.click(await screen.findByRole("radio", { name: /^You're wondering about it/ }));
  await user.click(nextBtn());
  await user.click(nextBtn());
  await user.click(await screen.findByRole("radio", { name: "One slow breath before I answer" }));
  await user.click(nextBtn());
  await noAxeViolations("lesson roleplay intro");
  await typedRoleplay();
  await user.click(nextBtn());

  // plan screen: prefilled with the role-play best phrase; the reminder downloads an .ics
  await heading("Your plan for next time");
  const box = screen.getByRole("textbox", { name: "then I'll say:" });
  await waitFor(() => expect((box as HTMLTextAreaElement).value).not.toBe(""));
  await user.click(screen.getByRole("button", { name: "Remind me tomorrow" }));
  await screen.findByText(/Your plan is saved/);
  expect(icsBlobs).toHaveLength(1);
  const ics = await readBlob(icsBlobs[0]!);
  expect(ics).toContain("BEGIN:VCALENDAR");
  expect(ics).toContain("BEGIN:VEVENT");
  expect(ics).toContain("\r\n");
  expect(ics).toMatch(/\r\nURL:https?:\/\/[^\r]+\/lessons\/m1_l1\r\n/);
  expect(ics).toContain("END:VCALENDAR");
  expect(ics).not.toContain(getToken()!);
  expect(ics).not.toMatch(/\{[A-Za-z]+\}/);
  await noAxeViolations("lesson plan screen");
  await user.click(nextBtn());

  // wrap: confidence check, completion
  await heading("You did it");
  for (const item of screen.getAllByRole("group")) {
    const radios = item.querySelectorAll("input");
    if (radios.length === 5) await user.click(radios[2] as HTMLInputElement);
  }
  await user.click(screen.getByRole("button", { name: "Finish lesson" }));
  await heading("Lesson complete");
  expect(screen.getByText("Talking so it lands")).toBeInTheDocument();
  expect(screen.getByText("Opens Jan 7")).toBeInTheDocument();
  await noAxeViolations("lesson complete");
}

async function simulateNextDay() {
  await user.click(await screen.findByRole("button", { name: "Simulate next day (demo)" }));
  await screen.findByText(/Day moved forward/);
}

async function startAtTodayWithDemoPaywall() {
  const token = "fake-token-journey";
  api.sessions.set(token, { answers: { q3_situation: "noticing" }, lastQuestionId: null, completed: true, subscribed: false, app: {} });
  setToken(token);
  renderAt("/paywall");
  await user.click(await screen.findByRole("checkbox"));
  await user.click(await screen.findByRole("button", { name: /Continue in demo mode/ }));
  await h1(/^Today with /);
  expect(here()).toBe("/today");
}

describe("app journey, persona A in demo mode", () => {
  it("lesson 1 in person to the retention loop, care card, billing and the gentle exit", async () => {
    installJourneyArea();
    await startAtTodayWithDemoPaywall();

    // welcome card: add a first name
    const welcome = await screen.findByRole("region", { name: "Welcome" });
    await user.type(within(welcome).getByRole("textbox"), PROFILE_NAME);
    await noAxeViolations("today fresh with welcome");
    await user.click(within(welcome).getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Welcome" })).toBeNull());
    expect(calls("PUT", "/profile")[0]!.body).toMatchObject({ displayName: PROFILE_NAME });

    await lessonOne("in_person");
    await user.click(screen.getByRole("link", { name: "Back to Today" }));
    await h1(/^Today with /);
    expect(await screen.findByText("Your next lesson opens on January 7.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Start lesson" })).toBeNull();
    await reload(/^Today with /);

    // day 2: check-in and the practice round appear; lesson 2 is still locked
    await simulateNextDay();
    const checkIn = await screen.findByRole("region", { name: "Check-in" });
    expect(screen.getByRole("link", { name: "Start practice" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Start lesson" })).toBeNull();
    await noAxeViolations("today day 2");
    await user.click(within(checkIn).getByRole("button", { name: "Yes" }));
    await user.click(within(checkIn).getByRole("button", { name: "It didn't help" }));
    expect(await within(checkIn).findByText("Look for a pattern")).toBeInTheDocument();
    expect(calls("POST", "/checkins")).toHaveLength(1);
    await noAxeViolations("check-in follow-ups");

    // care card: publish with the lesson phrase
    await router.navigate("/care-card");
    await h1(/care card/i);
    await user.click(await screen.findByRole("checkbox", { name: /wondering about tomorrow/ }));
    await user.click(screen.getByRole("button", { name: "Create private link" }));
    const link = (await screen.findByLabelText("Private link")) as HTMLInputElement;
    cardId = link.value.split("/card/")[1] ?? "";
    expect(cardId.length).toBeGreaterThan(0);
    await noAxeViolations("care card published");
    await reload(/care card/i);

    // practice round, saving a new phrase after the card was published: Today nudges
    await router.navigate("/today");
    await h1(/^Today with /);
    await user.click(await screen.findByRole("link", { name: "Start practice" }));
    await h1("2-minute practice");
    for (const [i, text] of ["zebra-practice-one", "zebra-practice-two"].entries()) {
      await user.type(await screen.findByRole("textbox", { name: "What would you say?" }), text);
      await user.click(screen.getByRole("button", { name: "Send" }));
      await screen.findByText("AI-generated");
      await user.click(screen.getByRole("button", { name: i === 0 ? "Next round" : "See your practice" }));
    }
    await heading("Your practice");
    await user.click(screen.getByRole("button", { name: /^Save/ }));
    await screen.findByRole("button", { name: "Saved" });
    await user.click(await roleplayContinue());
    await h1(/^Today with /);
    await user.click(await screen.findByRole("link", { name: "Update card" }));
    await h1(/care card/i);
    await user.click(await screen.findByRole("button", { name: "Update the card" }));
    await waitFor(() => expect(calls("PUT", "/care-card")).toHaveLength(1));

    // the sitter opens the public link with no token, in a second render
    const owner = getToken()!;
    view.unmount();
    clearToken();
    const before = sent.length;
    renderAt(`/card/${cardId}`);
    await h1(/^What works with/);
    const publicCalls = sent.slice(before);
    expect(publicCalls.map((c) => c.path)).toEqual([`/cards/${cardId}`]);
    expect(publicCalls.every((c) => c.token === null)).toBe(true);
    await noAxeViolations("public card");
    view.unmount();

    // the owner stops sharing; the same link now answers 410
    setToken(owner);
    renderAt("/care-card");
    await user.click(await screen.findByRole("button", { name: "Stop sharing" }));
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: /Stop sharing|Yes/ }));
    await waitFor(() => expect(screen.getByText("This link no longer works.")).toBeInTheDocument());
    view.unmount();
    clearToken();
    renderAt(`/card/${cardId}`);
    await screen.findByRole("heading", { name: /no longer|stopped/i });
    await noAxeViolations("public card revoked");
    view.unmount();
    setToken(owner);

    // the second simulated day opens lesson 2 and /plan shows it
    renderAt("/today");
    await h1(/^Today with /);
    await simulateNextDay();
    expect(await screen.findByRole("link", { name: "Start lesson" })).toBeInTheDocument();
    await router.navigate("/plan");
    await h1(/course/i);
    await user.click(await screen.findByRole("radio", { name: "All modules" }));
    await noAxeViolations("plan all modules");
    await router.navigate("/lessons/m1_l2");
    await h1("Talking so it lands");

    // visit sheet: edit and print
    await router.navigate("/visit-sheet");
    await h1(/next doctor visit/i);
    await user.type(screen.getByRole("textbox", { name: /Notes from family/ }), NOTE);
    await user.click(screen.getByRole("button", { name: "Print or save as PDF" }));
    await waitFor(() => expect(window.print).toHaveBeenCalled());
    expect(calls("PUT", "/visit-sheet").length).toBeGreaterThan(0);
    await noAxeViolations("visit sheet");
    await reload(/next doctor visit/i);
    expect((screen.getByRole("textbox", { name: /Notes from family/ }) as HTMLTextAreaElement).value).toBe(NOTE);

    // skills show the run
    await router.navigate("/skills");
    await h1("Your skills");
    await h2("Communication");
    await noAxeViolations("skills");

    // settings and the cancel flow
    await router.navigate("/settings");
    await h1("Settings");
    await user.click(await screen.findByRole("link", { name: "Cancel subscription" }));
    await user.click(await screen.findByRole("button", { name: "Cancel anyway" }));
    expect(await screen.findByText("Your plan is canceled")).toBeInTheDocument();
    expect(calls("POST", "/billing/cancel")).toHaveLength(1);
    await noAxeViolations("cancel done");

    expectPrivate();
  }, 120000);
});

function signedIn(token = "fake-token-journey"): string {
  api.sessions.set(token, { answers: {}, lastQuestionId: null, completed: true, subscribed: true, app: {} });
  setToken(token);
  return token;
}

describe("app journey, other runs", () => {
  it("lesson 1 on the phone variant, then reload keeps the lesson state on the server", async () => {
    installJourneyArea();
    signedIn();
    renderAt("/today");
    await h1(/^Today with /);
    await lessonOne("phone");
    await router.navigate("/today");
    await h1(/^Today with /);
    expect(await screen.findByText("Your next lesson opens on January 7.")).toBeInTheDocument();
    expectPrivate();
  }, 90000);

  it("the practice round in its multiple-choice fallback still finishes and returns to Today", async () => {
    installJourneyArea();
    signedIn();
    api.scenario.today = "day2";
    api.scenario.roleplayMode = ["fallback"];
    renderAt("/today");
    await h1(/^Today with /);
    await user.click(await screen.findByRole("link", { name: "Start practice" }));
    await h1("2-minute practice");
    await user.type(await screen.findByRole("textbox", { name: "What would you say?" }), REPLIES[0]!);
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText(/The practice partner isn't available right now/)).toBeInTheDocument();
    await noAxeViolations("practice fallback");
    expect(screen.queryByText(REPLIES[0]!)).toBeNull();
    const choices = await screen.findAllByRole("button", { name: /\w{4}/ });
    expect(choices.length).toBeGreaterThan(0);
    for (let i = 0; i < 4 && !screen.queryByRole("button", { name: "Finish practice" }); i++) {
      const option = screen
        .getAllByRole("button")
        .find((b) => b.getAttribute("aria-disabled") !== "true" && /You sound worried|left out/.test(b.textContent ?? ""));
      if (option) await user.click(option);
      const nextRound = screen.queryByRole("button", { name: "Next" });
      if (nextRound) await user.click(nextRound);
    }
    await user.click(await screen.findByRole("button", { name: "Finish practice" }));
    await heading("Nicely done");
    await user.click(await roleplayContinue());
    await h1(/^Today with /);
    expect(calls("POST", /\/turn$/)).toHaveLength(1);
    expectPrivate();
  }, 60000);

  it("past_due stays usable: the notice links to Settings, which still opens, and cancel works", async () => {
    signedIn();
    api.scenario.subscription = "past_due";
    renderAt("/today");
    const notice = (await screen.findByText(/update your card/i)).closest("[role=status]") as HTMLElement;
    expect(notice).not.toBeNull();
    await noAxeViolations("past_due notice");
    await user.click(within(notice).getByRole("link", { name: "Settings" }));
    await h1("Settings");
    expect(here()).toBe("/settings");
    await user.click(await screen.findByRole("link", { name: "Cancel subscription" }));
    await user.click(await screen.findByRole("button", { name: "Cancel anyway" }));
    expect(await screen.findByText("Your plan is canceled")).toBeInTheDocument();
    expect(getToken()).not.toBeNull();
  }, 30000);

  it("gentle exit on a fresh session ends at /goodbye with the token gone and no data left", async () => {
    const token = signedIn();
    api.sessions.get(token)!.app["phrases"] = [{ id: "p1", text: "kept?", source: "scenario", lessonId: null, savedAt: "x" }];
    renderAt("/settings");
    await h1("Settings");
    await user.click(await screen.findByRole("link", { name: /passed away|moved to a care facility/ }));
    await h2(/./);
    await user.click(await roleplayContinue());
    await noAxeViolations("gentle exit step 2");
    await user.click(await screen.findByRole("button", { name: "End my plan and delete my data" }));
    await h1("We're so sorry");
    expect(here()).toBe("/goodbye");
    expect(getToken()).toBeNull();
    expect(keysOf(window.localStorage)).toEqual([]);
    expect(api.sessions.has(token)).toBe(false);
    await noAxeViolations("goodbye");
    // a reload of /goodbye has no router state and goes home
    view.unmount();
    renderAt("/goodbye");
    await waitFor(() => expect(here()).toBe("/"));
    expect(logged.join("\n")).not.toContain("kept?");
    // the old token no longer opens anything
    setToken(token);
    const res = await fetch("/api/today", { headers: { "X-Session-Token": token } });
    expect(res.status).toBe(401);
  }, 30000);

  it("the lesson works from the keyboard alone", async () => {
    installJourneyArea();
    signedIn();
    renderAt("/lessons/m1_l1");
    await h1("When Mom asks again");

    async function tabTo(match: (el: Element) => boolean, limit = 80) {
      for (let i = 0; i < limit; i++) {
        await user.tab();
        if (document.activeElement && match(document.activeElement)) return;
      }
      throw new Error("never focused the target by keyboard");
    }
    const radio = (el: Element) => (el as HTMLInputElement).type === "radio";
    const button = (text: string | RegExp) => (el: Element) =>
      el.tagName === "BUTTON" && (typeof text === "string" ? el.textContent === text : text.test(el.textContent ?? ""));

    await tabTo(radio); // the first option of the setup question: "In person"
    await user.keyboard(" ");
    await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "9"));
    await tabTo(button("Continue"));
    await user.keyboard("{Enter}");
    await tabTo(radio); // first scenario reply; arrow keys move through the group
    for (let i = 1; i <= 3; i++) {
      await user.keyboard("{ArrowDown}"); // one answer is sent per change: let it settle before the next
      await waitFor(() => {
        expect(screen.getAllByRole("radio")[i]).toBeChecked();
        expect(screen.getAllByRole("radio")[i]).toBeEnabled();
      });
    }
    await screen.findByRole("button", { name: "Save this phrase" });
    await tabTo(button(/Save this phrase/));
    await user.keyboard("{Enter}");
    await screen.findByRole("button", { name: "Saved" });
    await tabTo(button("Continue"));
    await user.keyboard("{Enter}");
    await screen.findByRole("radio", { name: "Worry" });
    await noAxeViolations("keyboard lesson learn screen");
  }, 60000);
});

/** Nothing the user typed or the card id may reach a URL, storage, the console or a non-API request. */
function expectPrivate() {
  const secrets = [...REPLIES, "zebra-practice", NOTE];
  for (const entry of visited) {
    expect(entry).toMatch(/^\/[A-Za-z0-9_\-/]*$/);
    for (const secret of secrets) expect(entry).not.toContain(secret);
  }
  expect(keysOf(window.localStorage)).toEqual([TOKEN_KEY]);
  expect(keysOf(window.sessionStorage)).toEqual([]);
  const stored = JSON.stringify([...Object.entries(window.localStorage)]);
  for (const secret of secrets) expect(stored).not.toContain(secret);
  const consoleText = logged.filter((l) => !l.includes("Not implemented: HTMLCanvasElement")).join("\n");
  for (const secret of [...secrets, ...(cardId ? [cardId] : []), PROFILE_NAME]) expect(consoleText).not.toContain(secret);
  expect(sent.length).toBeGreaterThan(0);
  expect(sent.every((c) => c.url.startsWith("/api/"))).toBe(true);
  expect(sent.every((c) => !secrets.some((secret) => c.url.includes(secret)))).toBe(true);
  // The card id appears only in the public read; every other request carries the session token.
  if (cardId) expect(sent.filter((c) => c.url.includes(cardId)).every((c) => c.path === `/cards/${cardId}`)).toBe(true);
  const publicPaths = [/^\/cards\//, /^\/resources\//, /^\/pricing$/];
  for (const c of sent) {
    if (!publicPaths.some((re) => re.test(c.path))) expect(c.token, `${c.method} ${c.path}`).not.toBeNull();
  }
  if (cardId) expect(document.title).not.toContain(cardId);
}
