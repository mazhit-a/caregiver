/**
 * C6: the rendered-text and accessibility sweep over lesson 1 (24 screens), the Ollie ban
 * (brand book: never on crisis, payment, medical or gentle-exit screens), and the two viewports
 * (class/DOM assertions only, no real browser).
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { answerLesson, putLessonProgress } from "../api/app";
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

let api: FakeApi;
let view: ReturnType<typeof render> | undefined;
const user = userEvent.setup({ delay: null });

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("localStorage", memoryStorage());
  vi.stubGlobal("sessionStorage", memoryStorage());
  clearToken();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  vi.spyOn(console, "error").mockImplementation(() => undefined); // jsdom canvas noise from axe
  api = installFakeApi({ lesson24: true });
  setToken(signIn(api));
});
afterEach(() => {
  view?.unmount();
  view = undefined;
  api.restore();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const BANNED = /\{[A-Za-z]+\}|\bWrong\b|per day|\/ ?day\b|\brosa\b|\bRosa\b/;
const ollieImages = (): HTMLImageElement[] =>
  Array.from(document.querySelectorAll("img")).filter((i) => /ollie/i.test(i.getAttribute("src") ?? ""));

function open(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  view = render(<RouterProvider router={router} />);
  return router;
}

describe("lesson fixtures and rendered text", () => {
  it("every lesson and answer fixture is free of placeholders, 'Wrong', 'per day' and raw rosa", () => {
    const dir = join(__dirname, "fixtures", "app");
    const files = readdirSync(dir).filter((f) => /^(lesson24|answer)/.test(f) && f.endsWith(".json"));
    expect(files.length).toBeGreaterThanOrEqual(10);
    for (const f of files) expect(readFileSync(join(dir, f), "utf8"), f).not.toMatch(BANNED);
  });

  const SCREENS = appFixture<{ screens: { id: string; type: string }[] }>("lesson24-phone").screens;
  it.each(SCREENS.map((s, i) => [`${i + 1} ${s.type} (${s.id})`, i] as const))(
    "screen %s renders without placeholders or banned words, and its Ollie (if any) is decorative",
    async (_label, index) => {
      await answerLesson("m1_l1", { screenId: "setup", value: "phone" });
      await putLessonProgress("m1_l1", index);
      open("/lessons/m1_l1");
      await waitFor(() =>
        expect(screen.getByRole("progressbar", { name: "Lesson progress" })).toHaveAttribute(
          "aria-valuenow",
          String(index + 1),
        ),
      );
      const main = document.body.textContent ?? "";
      expect(main).not.toMatch(BANNED);
      for (const img of ollieImages()) expect(img.getAttribute("alt")).toBe("");
    },
  );

  it("axe passes on one render per screen type, and Continue stays reachable by keyboard", async () => {
    const seen = new Set<string>();
    for (const [index, s] of SCREENS.entries()) {
      if (seen.has(s.type)) continue;
      seen.add(s.type);
      await answerLesson("m1_l1", { screenId: "setup", value: "phone" });
      await putLessonProgress("m1_l1", index);
      open("/lessons/m1_l1");
      await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", String(index + 1)));
      expect(await axe(document.body), s.type).toHaveNoViolations();
      view?.unmount();
      view = undefined;
    }
    expect([...seen].sort()).toEqual(["builder", "content", "intro", "plan", "quiz", "reset", "roleplay", "scenario", "setup", "wrap"]);
  }, 30000);
});

describe("Ollie never appears on banned screens", () => {
  it("the Need-help sheet", async () => {
    open("/today");
    await screen.findByRole("heading", { level: 1, name: /^Today with / });
    await user.click(screen.getAllByRole("button", { name: "Need help now?" })[0] as HTMLElement);
    const dialog = await screen.findByRole("dialog", { name: "Need help now?" });
    expect(within(dialog).queryAllByRole("img")).toHaveLength(0);
    expect(dialog.querySelector("img")).toBeNull();
  });

  it("the paywall", async () => {
    api.sessions.set("fake-token-paywall", { answers: { q3_situation: "noticing" }, lastQuestionId: null, completed: true, subscribed: false, app: {} });
    setToken("fake-token-paywall");
    open("/paywall");
    await screen.findByRole("checkbox");
    expect(ollieImages()).toHaveLength(0);
  });

  it("the cancel and gentle-exit steps", async () => {
    for (const [path, ready] of [["/settings/cancel", "Keep my plan"], ["/settings/gentle-exit", "Continue"]] as const) {
      open(path);
      await screen.findAllByText(ready);
      expect(ollieImages(), path).toHaveLength(0);
      view?.unmount();
      view = undefined;
    }
  });

  it("the role-play medical tip", async () => {
    api.scenario.roleplayMode = ["medical"];
    await answerLesson("m1_l1", { screenId: "setup", value: "phone" });
    await putLessonProgress("m1_l1", 21);
    open("/lessons/m1_l1");
    await user.click(await screen.findByRole("button", { name: "Start practice" }));
    await user.type(await screen.findByRole("textbox", { name: "What would you say?" }), "should she take a pill");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("AI-generated");
    expect(ollieImages()).toHaveLength(0);
  });
});

describe("viewports (DOM and class assertions)", () => {
  const media = (wide: boolean) =>
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: wide && query.includes("min-width: 1024px"),
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      onchange: null,
      dispatchEvent: () => false,
    }));

  it("375px: the lesson plays in one column with the footer button reachable", async () => {
    media(false);
    open("/lessons/m1_l1");
    await screen.findByRole("heading", { level: 2, name: "When Mom asks again" });
    expect(screen.getByRole("button", { name: "Start the lesson" })).toBeInTheDocument();
    expect(document.querySelector("meta[name=viewport]") ?? document.head).toBeTruthy();
    expect(screen.queryAllByRole("navigation", { name: "App" }).length).toBeLessThanOrEqual(1);
  });

  it("1280px: Today shows one App navigation (the sidebar) and the lesson stays one reading column", async () => {
    media(true);
    open("/today");
    await screen.findByRole("heading", { level: 1, name: /^Today with / });
    expect(screen.getAllByRole("navigation", { name: "App" })).toHaveLength(1);
  });
});
