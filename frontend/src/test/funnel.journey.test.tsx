/* eslint-disable @typescript-eslint/no-non-null-assertion -- fixture lookups in tests */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, TOKEN_KEY } from "../api/session";
import { routes } from "../router";
import { type FakeApi, FAKE_CHECKOUT_ID, FAKE_CHECKOUT_URL, installFakeApi } from "./fakeApi";
import copy from "./fixtures/funnel-copy.json";
import giftB from "./fixtures/gift-b.json";
import quiz from "./fixtures/quiz.json";

vi.mock("../pages/funnel/checkoutRedirect", async (importActual) => ({
  ...(await importActual<typeof import("../pages/funnel/checkoutRedirect")>()),
  isStripeCheckoutUrl: (url: string) => url.startsWith("https://checkout.stripe.com/"),
  goToCheckout: vi.fn(),
}));
import { goToCheckout } from "../pages/funnel/checkoutRedirect";

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

/** Persona answers exactly as in content/funnel-qa.md section 1 (labels as the API shows them). */
interface Spec {
  q1: string;
  q2: string;
  q3: string;
  q5: string[] | null;
  q6: string;
  q7: string;
  q8: string;
  q9: string[];
  docs: [string, string, string];
  q11: string;
  q12: string;
  /** Raw answer ids that must never show up in a URL, storage key or console line. */
  secrets: string[];
}
const Q3 = quiz.questions[2]!.options!.map((o) => o.label);
const A: Spec = {
  q1: "My dad",
  q2: "65–74",
  q3: Q3[0]!,
  q5: null,
  q6: "Nearby, under an hour away",
  q7: "My brother or sister",
  q8: "Yes, part-time",
  q9: ["Not knowing what comes next"],
  docs: ["Have", "Have", "Have"],
  q11: "3",
  q12: "About 5 minutes",
  secrets: ["noticing", "nearby", "siblings", "part_time", "future", "65_74"],
};
const B: Spec = {
  q1: "My mom",
  q2: "75–84",
  q3: Q3[1]!,
  q5: ["Asks the same questions again and again", "Gets confused or upset in the late afternoon or evening"],
  q6: "Far away",
  q7: "Just me",
  q8: "Yes, full-time",
  q9: ["Knowing what to say", "Legal papers and money"],
  docs: ["Have", "Missing", "Not sure"],
  q11: "2",
  q12: "About 10 minutes",
  secrets: ["recent", "repeats", "evenings", "just_me", "full_time", "what_to_say", "legal_money", "75_84", "not_sure"],
};
const C: Spec = {
  q1: "My mom",
  q2: "85 or older",
  q3: Q3[3]!,
  q5: [quiz.questions[3]!.options![3]!.label, quiz.questions[3]!.options![4]!.label],
  q6: "With me",
  q7: "A paid caregiver or sitter",
  q8: "Not right now",
  q9: ["Safety at home", "My own exhaustion"],
  docs: ["Missing", "Missing", "Missing"],
  q11: "4",
  q12: "15 minutes or more",
  secrets: ["hospital", "refuses", "with_me", "paid", "not_now", "safety", "85plus"],
};

const WHEN_DONE = "/quiz/building";
const title = (id: string): string => quiz.questions.find((q) => q.id === id)!.title;

let api: FakeApi;
let logged: string[];
let router: ReturnType<typeof createMemoryRouter>;
let visited: string[];
const user = userEvent.setup({ delay: null });

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  clearToken();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  vi.mocked(goToCheckout).mockReset();
  logged = [];
  for (const level of ["log", "info", "warn", "error", "debug"] as const) {
    vi.spyOn(console, level).mockImplementation((...args: unknown[]) => {
      logged.push(args.map(String).join(" "));
    });
  }
  api = installFakeApi({ stripeConfigured: true });
});
afterEach(() => {
  api.restore();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function renderAt(path: string) {
  router = createMemoryRouter(routes, { initialEntries: [path] });
  visited = [path];
  router.subscribe((s) => visited.push(s.location.pathname + s.location.search + s.location.hash));
  return render(<RouterProvider router={router} />);
}
const here = (): string => router.state.location.pathname;
const cont = () => screen.getByRole("button", { name: "Continue" });
const h1 = (name: string | RegExp) => screen.findByRole("heading", { level: 1, name });

async function pick(label: string) {
  await user.click(await screen.findByRole("radio", { name: label }));
}
async function check(labels: string[]) {
  for (const l of labels) await user.click(await screen.findByRole("checkbox", { name: l }));
}
async function next(from: string) {
  await user.click(cont());
  await waitFor(() => expect(here()).not.toBe(from));
}

/** Answer one step (the page must already be on it). */
async function answerStep(id: string, spec: Spec) {
  const path = `/quiz/${id}`;
  await h1(title(id));
  switch (id) {
    case "q1_recipient": await pick(spec.q1); break;
    case "q2_age": await pick(spec.q2); break;
    case "q3_situation": await pick(spec.q3); break;
    case "q5_changes":
      if (spec.q5) await check(spec.q5);
      else await user.click(screen.getByRole("button", { name: "Skip" }));
      break;
    case "q6_living": await pick(spec.q6); break;
    case "q7_helpers": await pick(spec.q7); break;
    case "q8_work": await pick(spec.q8); break;
    case "q9_worries": await check(spec.q9); break;
    case "q10_documents": {
      const groups = await screen.findAllByRole("group");
      for (const [i, g] of groups.entries()) {
        await user.click(within(g).getByRole("radio", { name: spec.docs[i]! }));
      }
      break;
    }
    case "q11_confidence": await pick(spec.q11); break;
    case "q12_time": await pick(spec.q12); break;
    default: break; // interstitials
  }
  if (id === "q5_changes" && !spec.q5) await waitFor(() => expect(here()).not.toBe(path));
  else await next(path);
}

const STEPS = quiz.questions.map((q) => q.id);

/** Intro to the building route, answering every step. */
async function runQuiz(spec: Spec) {
  await user.click(await screen.findByRole("button", { name: "Start" }));
  for (const id of STEPS) await answerStep(id, spec);
  await waitFor(() => expect(here()).toBe(WHEN_DONE));
}

async function throughBuildingToPlan() {
  await h1(copy.loader.title);
  await user.click(await screen.findByRole("button", { name: copy.planPreview.cta }));
  await h1(copy.planPreview.title);
}
async function planToPaywall() {
  await user.click(screen.getByRole("button", { name: copy.planPreview.cta }));
  await h1(copy.paywall.headline);
}
const modules = () =>
  within(screen.getByRole("region", { name: "Your first 30 days" }))
    .getAllByRole("heading", { level: 3 })
    .map((h) => h.textContent);

function expectPrivate(spec: Spec) {
  for (const entry of visited) {
    expect(entry).toMatch(/^\/[a-z0-9_\-/]*(\?checkout=canceled|\?checkout_id=[\w]+)?$/);
    for (const s of spec.secrets) expect(entry).not.toContain(s);
  }
  expect(keysOf(window.localStorage)).toEqual([TOKEN_KEY]);
  expect(keysOf(window.sessionStorage)).toEqual([]);
  expect(window.localStorage.getItem(TOKEN_KEY)).toMatch(/^fake-token-/);
  const consoleText = logged.join("\n");
  for (const s of spec.secrets) expect(consoleText).not.toContain(s);
  for (const label of [spec.q1, spec.q3, spec.q6, spec.q7, spec.q8]) expect(consoleText).not.toContain(label);
  const urls = vi.mocked(fetch).mock.calls.map((c) => String(c[0]));
  expect(urls.length).toBeGreaterThan(0);
  expect(urls.every((u) => u.startsWith("/api/"))).toBe(true);
  expect(urls.every((u) => !spec.secrets.some((s) => u.includes(s)))).toBe(true);
}

const planExpect = {
  A: { first30: ["Talking with Dad", "Before the diagnosis", "Hard moments"] },
  B: {
    first30: ["Talking with Mom", "While she can still decide", "Hard moments"],
    heard:
      "Mom was diagnosed in the last few months. Mom lives far away. You're handling most of it alone, and you work full-time. What worries you most: knowing what to say and legal papers and money.",
  },
  C: { first30: ["Talking with Mom", "Safe home, calmer days", "Hard moments"] },
} as const;

describe("full funnel journey", () => {
  it("persona A to demo: plan, gift, paywall, demo, Today; no answer leaks", async () => {
    const { container } = renderAt("/quiz");
    await h1("Let's build your plan");
    await runQuiz(A);
    await throughBuildingToPlan();
    expect(modules()).toEqual(planExpect.A.first30);
    expect(screen.getAllByText(/Dad/).length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("{");
    expect(await axe(container)).toHaveNoViolations();

    await user.click(await screen.findByRole("link", { name: /free sheet|Download/i }));
    await h1(giftB.title.replace("Mom", "Dad"));
    expect(here()).toBe("/your-plan/gift");
    await user.click(screen.getByRole("link", { name: /Back to your plan/ }));
    await h1(copy.planPreview.title);

    await planToPaywall();
    await user.click(screen.getByRole("button", { name: /Continue in demo mode/ }));
    await h1(/^Today/);
    expect(here()).toBe("/today");
    expect(api.calls.filter((c) => c.path === "/billing/demo")).toHaveLength(1);
    expectPrivate(A);
  }, 60000);

  it("persona B to Stripe: checkout URL assigned, return paid, Today", async () => {
    renderAt("/quiz");
    await runQuiz(B);
    await throughBuildingToPlan();
    expect(modules()).toEqual(planExpect.B.first30);
    expect(screen.getByText(planExpect.B.heard)).toBeInTheDocument();
    await planToPaywall();

    const plan = copy.paywall.plans[0]!;
    await user.click(screen.getByRole("button", { name: plan.payButtonLabel }));
    await waitFor(() => expect(goToCheckout).toHaveBeenCalledWith(FAKE_CHECKOUT_URL));
    expect(goToCheckout).toHaveBeenCalledTimes(1);
    expect(here()).toBe("/paywall");

    // Stripe sends the browser back.
    await router.navigate(`/checkout/return?checkout_id=${FAKE_CHECKOUT_ID}`);
    await h1(copy.paywall.states.success);
    expect(api.calls.filter((c) => c.path.startsWith("/billing/checkout/"))).toHaveLength(1);
    expect(here()).toBe("/checkout/return");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await h1(/^Today/);
    expectPrivate(B);
  }, 60000);

  it("persona C cancel path: back at the paywall with the banner, then demo works", async () => {
    const first = renderAt("/quiz");
    await runQuiz(C);
    await throughBuildingToPlan();
    expect(modules()).toEqual(planExpect.C.first30);
    expect(screen.getByText(/^After a hospital stay/)).toBeInTheDocument();
    await planToPaywall();
    await user.click(screen.getByRole("button", { name: copy.paywall.plans[0]!.payButtonLabel }));
    await waitFor(() => expect(goToCheckout).toHaveBeenCalled());

    // Stripe's cancel link is a full page load: a fresh paywall, nothing carried over.
    first.unmount();
    renderAt("/paywall?checkout=canceled");
    expect(await screen.findByRole("status")).toHaveTextContent(copy.paywall.states.returnedCanceled);
    expect(api.calls.filter((c) => c.path === "/billing/demo")).toHaveLength(0);
    await user.click(screen.getByRole("button", { name: /Continue in demo mode/ }));
    await h1(/^Today/);
    expectPrivate(C);
  }, 60000);

  it("browser Back through the quiz keeps every answer", async () => {
    renderAt("/quiz");
    await user.click(await screen.findByRole("button", { name: "Start" }));
    const answered = ["q1_recipient", "q2_age", "q3_situation", "q5_changes", "reassure_1", "q6_living", "q7_helpers"];
    for (const id of answered) await answerStep(id, B);
    await h1(title("q8_work"));
    for (const id of [...answered].reverse()) {
      await user.click(await screen.findByRole("link", { name: "Back" }));
      await waitFor(() => expect(here()).toBe(`/quiz/${id}`));
      await h1(title(id)).catch(() => screen.findByRole("heading", { level: 1 }));
    }
    expect(here()).toBe("/quiz/q1_recipient");
    expect(((await screen.findByRole("radio", { name: B.q1 })) as HTMLInputElement).checked).toBe(true);
    await user.click(cont());
    await h1(title("q2_age"));
    expect(((await screen.findByRole("radio", { name: B.q2 })) as HTMLInputElement).checked).toBe(true);
    // And the browser's own Back button behaves the same way.
    await router.navigate(-1);
    await h1(title("q1_recipient"));
    expect(((await screen.findByRole("radio", { name: B.q1 })) as HTMLInputElement).checked).toBe(true);
  }, 60000);

  it("reload at every step resumes with the same session and no second session", async () => {
    const first = renderAt("/quiz");
    await user.click(await screen.findByRole("button", { name: "Start" }));
    let view = first;
    for (const id of STEPS) {
      await answerStep(id, B);
      const where = here();
      view.unmount();
      view = renderAt(where);
      await waitFor(() => expect(here()).toBe(where === WHEN_DONE ? WHEN_DONE : where));
      if (where === WHEN_DONE) break;
      const stepId = here().replace("/quiz/", "");
      await h1(title(stepId));
    }
    expect(api.calls.filter((c) => c.method === "POST" && c.path === "/session")).toHaveLength(1);
    // Reload on the building screen, the plan, the gift and the paywall.
    for (const path of [WHEN_DONE, "/your-plan", "/your-plan/gift", "/paywall"]) {
      view.unmount();
      view = renderAt(path);
      if (path === WHEN_DONE) {
        await h1(copy.loader.title);
        await user.click(await screen.findByRole("button", { name: copy.planPreview.cta }));
        await h1(copy.planPreview.title);
        view.unmount();
        view = renderAt("/your-plan");
      }
      await waitFor(() => expect(here()).toBe(path === WHEN_DONE ? "/your-plan" : path));
      if (path === "/your-plan") await h1(copy.planPreview.title);
      if (path === "/your-plan/gift") await h1(/.+/);
      if (path === "/paywall") await h1(copy.paywall.headline);
    }
    expect(api.calls.filter((c) => c.method === "POST" && c.path === "/session")).toHaveLength(1);
    expectPrivate(B);
  }, 90000);

  it("changing Q1 and Q3 on the way back changes the names and the plan", async () => {
    renderAt("/quiz");
    await runQuiz(B);
    await throughBuildingToPlan();
    expect(modules()[0]).toBe("Talking with Mom");
    await user.click(screen.getByRole("link", { name: /Change my answers/ }));
    await h1(title("q1_recipient"));
    expect(here()).toBe("/quiz/q1_recipient");
    await answerStep("q1_recipient", A);
    await answerStep("q2_age", B); // unchanged
    await answerStep("q3_situation", A);
    // The rest are already answered: Continue only.
    for (const id of STEPS.slice(3)) {
      await h1(title(id));
      await next(`/quiz/${id}`);
    }
    await waitFor(() => expect(here()).toBe(WHEN_DONE));
    await throughBuildingToPlan();
    expect(modules()).toEqual(planExpect.A.first30);
    expect(screen.queryByText(planExpect.B.heard)).toBeNull();
    expect(screen.getAllByText(/Dad/).length).toBeGreaterThan(0);
    expect(api.calls.filter((c) => c.method === "PUT" && c.path.startsWith("/quiz/answers/")).length).toBeGreaterThan(13);
  }, 90000);

  it("keyboard only: persona A from the intro to the plan, no pointer", async () => {
    renderAt("/quiz");
    await h1("Let's build your plan");

    const accName = (el: Element): string =>
      el.getAttribute("aria-label") ?? el.closest("label")?.textContent ?? el.textContent ?? "";
    /** Tab until the control is focused; for radio groups fall back to arrow keys. */
    async function focus(role: "radio" | "checkbox" | "button" | "link", label: string) {
      await screen.findByRole(role, { name: label });
      for (let i = 0; i < 60; i++) {
        const el = document.activeElement;
        if (el && el !== document.body && el.getAttribute("role") !== "dialog") {
          const isTarget = accName(el).trim() === label && (el.getAttribute("type") === role || el.tagName.toLowerCase() === (role === "button" ? "button" : "a") || el.getAttribute("role") === role);
          if (isTarget) return;
        }
        await user.tab();
        const now = document.activeElement;
        if (role === "radio" && now instanceof HTMLInputElement && now.type === "radio") {
          const target = (screen.getByRole("radio", { name: label }) as HTMLInputElement);
          if (target.name === now.name) {
            for (let k = 0; k < 8 && document.activeElement !== target; k++) await user.keyboard("{ArrowDown}");
            if (document.activeElement === target) return;
          }
        }
      }
      throw new Error(`could not reach ${role} "${label}" by keyboard`);
    }
    async function keyPick(label: string) {
      await focus("radio", label);
      if (!(document.activeElement as HTMLInputElement).checked) await user.keyboard(" ");
      expect((document.activeElement as HTMLInputElement).checked).toBe(true);
    }
    async function keyContinue(from: string) {
      await focus("button", "Continue");
      await user.keyboard("{Enter}");
      await waitFor(() => expect(here()).not.toBe(from));
    }

    await focus("button", "Start");
    await user.keyboard("{Enter}");
    for (const id of STEPS) {
      await h1(title(id));
      const path = `/quiz/${id}`;
      const single: Record<string, string> = {
        q1_recipient: A.q1, q2_age: A.q2, q3_situation: A.q3, q6_living: A.q6, q7_helpers: A.q7,
        q8_work: A.q8, q11_confidence: A.q11, q12_time: A.q12,
      };
      if (single[id]) await keyPick(single[id]);
      else if (id === "q5_changes") {
        await focus("button", "Skip");
        await user.keyboard("{Enter}");
        await waitFor(() => expect(here()).not.toBe(path));
        continue;
      } else if (id === "q9_worries") {
        await focus("checkbox", A.q9[0]!);
        await user.keyboard(" ");
      } else if (id === "q10_documents") {
        for (const g of await screen.findAllByRole("group")) {
          const have = within(g).getByRole("radio", { name: "Have" });
          for (let i = 0; i < 60 && document.activeElement !== have; i++) {
            await user.tab();
            const now = document.activeElement;
            if (now instanceof HTMLInputElement && now.name === (have as HTMLInputElement).name && now !== have) {
              await user.keyboard("{ArrowUp}{ArrowUp}");
            }
          }
          if (!(have as HTMLInputElement).checked) await user.keyboard(" ");
          expect((have as HTMLInputElement).checked).toBe(true);
        }
      }
      await keyContinue(path);
    }
    await h1(copy.loader.title);
    await focus("button", copy.planPreview.cta);
    await user.keyboard("{Enter}");
    await h1(copy.planPreview.title);
    expect(modules()).toEqual(planExpect.A.first30);
    expect(keysOf(window.localStorage)).toEqual([TOKEN_KEY]);
  }, 120000);

  it("a locked quiz sends the subscribed visitor to Today, from the quiz and from the paywall", async () => {
    const first = renderAt("/quiz");
    await runQuiz(A);
    await throughBuildingToPlan();
    await planToPaywall();
    await user.click(screen.getByRole("button", { name: /Continue in demo mode/ }));
    await h1(/^Today/);
    let view = first;
    for (const path of ["/quiz", "/quiz/q3_situation", "/paywall"]) {
      view.unmount();
      view = renderAt(path);
      await waitFor(() => expect(here()).toBe("/today"));
      await h1(/^Today/);
    }
  }, 60000);

  it("a lost session returns to the quiz intro with the restore message", async () => {
    renderAt("/quiz");
    await runQuiz(A);
    await throughBuildingToPlan();
    api.sessions.clear();
    renderAt("/your-plan");
    await waitFor(() => expect(here()).toBe("/quiz"));
    expect(await screen.findByText(/We couldn't restore your plan/)).toBeInTheDocument();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Start" }));
    await h1(title("q1_recipient"));
    expect(api.calls.filter((c) => c.method === "POST" && c.path === "/session").length).toBe(2);
  }, 60000);

  it("/paywall without a plan goes to the quiz", async () => {
    const first = renderAt("/quiz");
    await user.click(await screen.findByRole("button", { name: "Start" }));
    await h1(title("q1_recipient"));
    first.unmount();
    renderAt("/paywall");
    await waitFor(() => expect(here()).toMatch(/^\/quiz(\/q1_recipient)?$/));
    await h1(/.+/);
    expect(screen.queryByRole("button", { name: /Continue in demo mode/ })).toBeNull();
  });

  it("gift sheet opens from the plan with the persona title and the safety footer", async () => {
    renderAt("/quiz");
    await runQuiz(B);
    await throughBuildingToPlan();
    await user.click(await screen.findByRole("link", { name: /free sheet|Download/i }));
    await h1(giftB.title);
    expect(here()).toBe("/your-plan/gift");
    expect(screen.getByText(giftB.footer)).toBeInTheDocument();
  }, 60000);
});
