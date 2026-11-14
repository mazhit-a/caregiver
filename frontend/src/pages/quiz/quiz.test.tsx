/* eslint-disable @typescript-eslint/no-non-null-assertion -- fixture lookups in tests */
import { readFileSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, TOKEN_KEY } from "../../api/session";
import { routes } from "../../router";
import { type FakeApi, installFakeApi } from "../../test/fakeApi";
import quiz from "../../test/fixtures/quiz.json";
import { QUIZ_HEALTH_NOTE } from "./quizCopy";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

/** jsdom under newer Node can lack a working localStorage: use a plain in-memory one. */
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
const storageKeys = (): string[] =>
  Array.from({ length: window.localStorage.length }, (_, i) => window.localStorage.key(i) ?? "");

let fake: FakeApi;
beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("localStorage", memoryStorage());
  clearToken();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  fake = installFakeApi();
});
afterEach(() => {
  fake.restore();
  vi.unstubAllGlobals();
});

const user = userEvent.setup;
const renderAt = (path: string) => {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return { router, ...render(<RouterProvider router={router} />) };
};
const sessionPosts = () => fake.calls.filter((c) => c.method === "POST" && c.path === "/session");
const cont = () => screen.getByRole("button", { name: "Continue" });

async function answerSingle(label: string) {
  await user().click(await screen.findByRole("radio", { name: label }));
  await user().click(cont());
}

describe("quiz flow", () => {
  it("intro: Start creates exactly one session and opens Q1; axe clean", async () => {
    const { router, container } = renderAt("/quiz");
    expect(await screen.findByRole("heading", { level: 1, name: "Let's build your plan" })).toBeTruthy();
    expect(await axe(container)).toHaveNoViolations();
    const start = screen.getByRole("button", { name: "Start" });
    await user().dblClick(start);
    await waitFor(() => expect(router.state.location.pathname).toBe("/quiz/q1_recipient"));
    expect(sessionPosts()).toHaveLength(1);
    expect(window.localStorage.getItem(TOKEN_KEY)).toBe("fake-token-1");
    expect(await screen.findByText("1 of 11")).toBeTruthy();
  });

  it("Continue is disabled until answered, then saves, advances, and Back keeps the answer", async () => {
    const { router, container } = renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    await screen.findByRole("heading", { name: quiz.questions[0]!.title });
    expect(cont().getAttribute("aria-disabled")).toBe("true");
    await user().click(screen.getByRole("radio", { name: "My dad" }));
    expect(await axe(container)).toHaveNoViolations();
    await user().click(cont());
    await waitFor(() => expect(router.state.location.pathname).toBe("/quiz/q2_age"));
    expect(fake.calls.filter((c) => c.method === "PUT")).toHaveLength(1);
    await screen.findByRole("heading", { name: quiz.questions[1]!.title }); // the loading screen also has a Back link
    await user().click(await screen.findByRole("link", { name: "Back" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/quiz/q1_recipient"));
    expect(((await screen.findByRole("radio", { name: "My dad" })) as HTMLInputElement).checked).toBe(true);
  });

  it("shows server text re-fetched after an answer (next title comes from the API)", async () => {
    renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    await screen.findByRole("heading", { name: quiz.questions[0]!.title });
    fake.inject({
      method: "GET",
      path: "/quiz",
      status: 200,
      body: {
        questions: quiz.questions.map((q) =>
          q.id === "q2_age" ? { ...q, title: "How old is Mom?" } : q,
        ),
        answers: { q1_recipient: "mom" },
        branch: null,
        lastQuestionId: "q1_recipient",
        completed: false,
        locked: false,
      },
    });
    await answerSingle("My mom");
    expect(await screen.findByRole("heading", { name: "How old is Mom?" })).toBeTruthy();
  });

  it("Q3 and Q5 show the health note; Q5 Skip sends an empty list", async () => {
    renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    for (const [, label] of [
      ["q1", "My mom"],
      ["q2", "Under 65"],
    ] as const) {
      expect(screen.queryByText(QUIZ_HEALTH_NOTE)).toBeNull();
      await answerSingle(label);
    }
    expect(await screen.findByText(QUIZ_HEALTH_NOTE)).toBeTruthy();
    await answerSingle(quiz.questions[2]!.options![0]!.label);
    expect(await screen.findByText(QUIZ_HEALTH_NOTE)).toBeTruthy();
    await user().click(screen.getByRole("button", { name: "Skip" }));
    await screen.findByRole("heading", { name: quiz.questions[4]!.title });
    expect(fake.sessions.get("fake-token-1")!.answers["q5_changes"]).toEqual([]);
  });

  it("reload mid-quiz resumes at the first unanswered question with answers filled", async () => {
    const first = renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    await answerSingle("My mom");
    await screen.findByRole("heading", { name: quiz.questions[1]!.title });
    first.unmount();
    const { router } = renderAt("/quiz");
    await waitFor(() => expect(router.state.location.pathname).toBe("/quiz/q2_age"));
    expect(sessionPosts()).toHaveLength(1);
    await screen.findByRole("heading", { name: quiz.questions[1]!.title }); // the loading screen also has a Back link
    await user().click(await screen.findByRole("link", { name: "Back" }));
    expect(((await screen.findByRole("radio", { name: "My mom" })) as HTMLInputElement).checked).toBe(true);
  });

  it("redirects a deep link past the resume point", async () => {
    renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    await screen.findByRole("heading", { name: quiz.questions[0]!.title });
    const { router } = renderAt("/quiz/q11_confidence");
    await waitFor(() => expect(router.state.location.pathname).toBe("/quiz/q1_recipient"));
  });

  it("locked quiz goes to /today; completed quiz re-completes and goes to the plan", async () => {
    renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    await screen.findByRole("heading", { name: quiz.questions[0]!.title });
    const state = fake.sessions.get("fake-token-1")!;
    state.subscribed = true;
    const locked = renderAt("/quiz");
    await waitFor(() => expect(locked.router.state.location.pathname).toBe("/today"));
    state.subscribed = false;
    state.completed = true;
    for (const q of quiz.questions) if (q.type !== "interstitial") state.answers[q.id] = "x";
    const done = renderAt("/quiz");
    await waitFor(() => expect(done.router.state.location.pathname).toBe("/your-plan"));
    expect(fake.calls.some((c) => c.path === "/quiz/complete")).toBe(true);
  });

  it("401 clears the token and shows the restore message on a fresh intro", async () => {
    window.localStorage.setItem(TOKEN_KEY, "unknown-token");
    renderAt("/quiz");
    expect(await screen.findByText(/We couldn't restore your plan/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Start" })).toBeTruthy();
    expect(window.localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("429 on creation shows the rate-limit message and works on retry", async () => {
    fake.scenario.sessionRateLimited = true;
    renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    expect(await screen.findByText(/try again in a minute/)).toBeTruthy();
    fake.scenario.sessionRateLimited = false;
    await user().click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: quiz.questions[0]!.title })).toBeTruthy();
  });

  it("a failed save keeps the selection and shows a retry path", async () => {
    renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    await user().click(await screen.findByRole("radio", { name: "My mom" }));
    fake.injectError("PUT", "/quiz/answers/*", 500, "server_error");
    await user().click(cont());
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect((screen.getByRole("radio", { name: "My mom" }) as HTMLInputElement).checked).toBe(true);
    await user().click(cont());
    expect(await screen.findByRole("heading", { name: quiz.questions[1]!.title })).toBeTruthy();
  });

  it("runs the whole quiz to the building route; no answers in URLs; only the token in storage", async () => {
    const { router, container } = renderAt("/quiz");
    await user().click(await screen.findByRole("button", { name: "Start" }));
    const seen: string[] = [];
    for (let guard = 0; guard < 20 && router.state.location.pathname !== "/quiz/building"; guard++) {
      const path = router.state.location.pathname;
      seen.push(router.state.location.pathname + router.state.location.search);
      const q = quiz.questions.find((x) => `/quiz/${x.id}` === path);
      if (!q) {
        await new Promise((r) => setTimeout(r, 0));
        continue;
      }
      await screen.findByRole("heading", { level: 1, name: q.title });
      if (q.type === "single") await user().click(screen.getAllByRole("radio")[0]!);
      if (q.type === "multi") await user().click(screen.getAllByRole("checkbox")[0]!);
      if (q.type === "grid") {
        for (const r of screen.getAllByRole("group")) {
          await user().click(r.querySelectorAll<HTMLInputElement>("input")[0]!);
        }
      }
      if (q.type === "scale") await user().click(screen.getAllByRole("radio")[2]!);
      if (q.type === "grid") expect(await axe(container)).toHaveNoViolations();
      await user().click(cont());
      await waitFor(() => expect(router.state.location.pathname).not.toBe(path));
    }
    expect(router.state.location.pathname).toBe("/quiz/building");
    expect(seen.length).toBe(13);
    expect(seen.every((p) => /^\/quiz(\/[a-z0-9_]+)?$/.test(p))).toBe(true);
    expect(storageKeys()).toEqual([TOKEN_KEY]);
  });
});

describe("copy", () => {
  it("health note matches content/funnel-copy.json", () => {
    const c = JSON.parse(readFileSync("../content/funnel-copy.json", "utf8")) as {
      quiz: { healthNote: string };
    };
    expect(QUIZ_HEALTH_NOTE).toBe(c.quiz.healthNote);
  });
});
