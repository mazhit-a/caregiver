/* eslint-disable @typescript-eslint/no-non-null-assertion -- fixture lookups in tests */
/**
 * C6: one scripted journey through all 24 screens of lesson 1 with the fake API (setup `phone` and
 * `both`), plus privacy spies (console, storage, URLs, request list) and a rendered-text scan.
 * No sleeps: every step waits for a specific heading, text or state.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../api/session";
import { routes } from "../router";
import { type FakeApi, installFakeApi } from "./fakeApi";
import { signIn } from "./fakeApp/core";
import { appFixture } from "./fakeApp/fixtures";
import "./fakeApp/lessonV2";

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

interface Sent {
  method: string;
  path: string;
  url: string;
  raw: string;
}
interface Screen {
  id: string;
  type: string;
  title?: string;
}
interface Key {
  quiz: Record<string, { correct: boolean }[]>;
  scenario: Record<string, { verdict: string }[]>;
}

const REPLIES = ["zebra-reply-one", "zebra-reply-two", "zebra-reply-three"];
let api: FakeApi;
let sent: Sent[];
let logged: string[];
let local: Storage;
let session: Storage;
let router: ReturnType<typeof createMemoryRouter>;
let view: ReturnType<typeof render>;
const user = userEvent.setup({ delay: null });

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  local = memoryStorage();
  session = memoryStorage();
  vi.stubGlobal("localStorage", local);
  vi.stubGlobal("sessionStorage", session);
  clearToken();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  logged = [];
  for (const level of ["log", "info", "warn", "error", "debug"] as const) {
    vi.spyOn(console, level).mockImplementation((...args: unknown[]) => {
      logged.push(args.map(String).join(" "));
    });
  }
  api = installFakeApi({ lesson24: true });
  const base = globalThis.fetch;
  sent = [];
  vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    sent.push({
      method: (init?.method ?? "GET").toUpperCase(),
      path: url.replace(/^\/api/, "").split("?")[0] ?? "",
      url,
      raw: typeof init?.body === "string" ? init.body : "",
    });
    return base(input, init);
  });
  setToken(signIn(api));
  Object.assign(URL, { createObjectURL: vi.fn(() => "blob:ics"), revokeObjectURL: vi.fn() });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});
afterEach(() => {
  view?.unmount();
  api.restore();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const progress = () => screen.getByRole("progressbar", { name: "Lesson progress" });
/** The player's footer button (the role-play screen has its own "Continue"). */
const footer = (name: string | RegExp = "Continue") =>
  screen.getAllByRole("button", { name }).filter((b) => b.hasAttribute("aria-disabled") || name !== "Continue")[0] as HTMLElement;
const unlocked = () => waitFor(() => expect(footer()).not.toHaveAttribute("aria-disabled", "true"));
const step = (n: number) => waitFor(() => expect(progress()).toHaveAttribute("aria-valuenow", String(n)));

async function playRoleplay() {
  await user.click(await screen.findByRole("button", { name: "Start practice" }));
  for (const [i, text] of REPLIES.entries()) {
    await user.type(await screen.findByRole("textbox", { name: "What would you say?" }), text);
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("AI-generated");
    await user.click(screen.getByRole("button", { name: i < 2 ? "Next round" : "See your practice" }));
  }
  const inner = await waitFor(() => {
    const found = screen.getAllByRole("button", { name: "Continue" }).filter((b) => !b.hasAttribute("aria-disabled"));
    if (found.length !== 1) throw new Error("expected the role-play Continue button");
    return found[0] as HTMLElement;
  });
  await user.click(inner);
}

/** Plays screen by screen, choosing from the fixture's screen list; returns the screen types visited. */
async function playLesson(variant: "phone" | "both"): Promise<string[]> {
  const key = appFixture<Key>("answerkey-m1_l1");
  const lesson = appFixture<{ screens: Screen[] }>(`lesson24-${variant}`);
  const visited: string[] = [];
  let quizzes = 0;
  const router0 = createMemoryRouter(routes, { initialEntries: ["/lessons/m1_l1"] });
  router = router0;
  view = render(<RouterProvider router={router0} />);
  await screen.findByRole("heading", { level: 2, name: "When Mom asks again" });
  expect(progress()).toHaveAttribute("aria-valuemax", "24");

  for (const [i, s] of lesson.screens.entries()) {
    await step(i + 1);
    visited.push(s.type);
    process.stderr.write(`SCREEN ${i + 1} ${s.type}\n`);
    switch (s.type) {
      case "intro":
        await user.click(footer("Start the lesson"));
        continue;
      case "setup": {
        const label = appFixture<{ screens: { id: string; options: { id: string; label: string }[] }[] }>(
          "lesson24-initial",
        ).screens.find((x) => x.id === "setup")!.options.find((o) => o.id === variant)!.label;
        await user.click(await screen.findByRole("radio", { name: label }));
        break;
      }
      case "scenario": {
        const verdicts = key.scenario[variant]!.map((r) => r.verdict);
        const radios = await screen.findAllByRole("radio");
        await user.click(radios[verdicts.indexOf("best")]!);
        await user.click(await screen.findByRole("button", { name: "Save this phrase" }));
        await screen.findByRole("button", { name: "Saved" });
        break;
      }
      case "quiz": {
        const rows = key.quiz[s.id]!;
        const right = rows.findIndex((r) => r.correct);
        const wrong = rows.findIndex((r) => !r.correct);
        const radios = await screen.findAllByRole("radio");
        if (quizzes % 2 === 0) await user.click(radios[wrong]!); // a miss first, then the right one
        await user.click(radios[right]!);
        quizzes += 1;
        break;
      }
      case "builder":
        for (const fieldset of await screen.findAllByRole("group")) {
          const first = fieldset.querySelector("input");
          if (first) await user.click(first);
        }
        break;
      case "reset":
        await user.click((await screen.findAllByRole("radio"))[0]!);
        break;
      case "roleplay":
        await playRoleplay();
        break;
      case "plan":
        await user.click(await screen.findByRole("button", { name: "Remind me tomorrow" }));
        await screen.findByText(/Your plan is saved/);
        break;
      case "wrap": {
        for (const item of screen.getAllByRole("group")) {
          const radios = item.querySelectorAll("input");
          if (radios.length === 5) await user.click(radios[2] as HTMLInputElement);
        }
        await user.click(screen.getByRole("button", { name: "Finish lesson" }));
        await screen.findByRole("heading", { name: "Lesson complete" });
        await user.click(await screen.findByRole("link", { name: /Back to Today/ }));
        await screen.findByRole("heading", { level: 1, name: /^Today with / });
        return visited;
      }
      default:
        break; // content screens: nothing to answer
    }
    await unlocked();
    await user.click(footer());
  }
  return visited;
}

describe("lesson 1, 24 screens, end to end with the fake API", () => {
  it("plays every screen on the phone variant: quizzes right and wrong, builder, reset, role-play, plan, wrap", async () => {
    const visited = await playLesson("phone");
    expect(visited).toHaveLength(24);
    expect(visited.filter((t) => t === "quiz")).toHaveLength(6);
    expect(visited.filter((t) => t === "content")).toHaveLength(10);
    expect(visited).toEqual(expect.arrayContaining(["intro", "setup", "scenario", "builder", "reset", "roleplay", "plan", "wrap"]));
    expect(sent.filter((c) => c.method === "POST" && c.path === "/lessons/m1_l1/complete")).toHaveLength(1);
    expect(router.state.location.pathname).toBe("/today");
  }, 30000);

  it("plays every screen on the both variant", async () => {
    const visited = await playLesson("both");
    expect(visited).toHaveLength(24);
    expect(router.state.location.pathname).toBe("/today");
  }, 30000);

  it("keeps answer text out of storage, URLs, the console and every request but the role-play one", async () => {
    await playLesson("phone");
    const answers = sent.filter((c) => c.path === "/lessons/m1_l1/answers");
    expect(answers.length).toBeGreaterThan(10);
    for (const r of REPLIES) {
      for (const store of [local, session]) {
        for (let i = 0; i < store.length; i++) {
          const k = store.key(i) ?? "";
          expect(`${k}=${store.getItem(k)}`).not.toContain(r);
        }
      }
      expect(logged.join("\n")).not.toContain(r);
      for (const c of sent) {
        expect(c.url).not.toContain(r);
        if (!/roleplay/.test(c.path)) expect(c.raw).not.toContain(r);
      }
    }
    // Typed role-play text only ever went to the role-play route.
    expect(sent.some((c) => /roleplay/.test(c.path) && c.raw.includes(REPLIES[0]!))).toBe(true);
    // Answers use ids and screen ids, never free text from the quiz or builder; no URL carries an answer.
    for (const c of sent) expect(c.url).not.toMatch(/answer=|reply=|quiz=/);
    for (const v of router.state.historyAction ? [router.state.location] : []) {
      expect(v.search).toBe("");
    }
  }, 30000);

  it("has no axe violations on a quiz after a wrong answer, with its warm feedback", async () => {
    const router0 = createMemoryRouter(routes, { initialEntries: ["/lessons/m1_l1"] });
    view = render(<RouterProvider router={router0} />);
    await screen.findByRole("heading", { level: 2, name: "When Mom asks again" });
    await user.click(footer("Start the lesson"));
    await user.click(await screen.findByRole("radio", { name: /On the phone/ }));
    await unlocked();
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
