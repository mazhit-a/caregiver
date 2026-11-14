import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../../../api/session";
import type { RoleplayFinish } from "../../../api/appTypes";
import type { AppContext } from "../../../layout/app/appContext";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import TodayPage from "../TodayPage";
import { WithAppCopy } from "../../../test/withAppCopy";
import PracticeRoundPage from "./PracticeRoundPage";
import { RoleplayRoom } from "./RoleplayRoom";

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
const done = vi.fn<(finish: RoleplayFinish | null) => void>();
const openHelp = vi.fn();

beforeEach(() => {
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  Object.defineProperty(window, "sessionStorage", { value: memoryStorage(), configurable: true });
  window.scrollTo = vi.fn();
  clearToken();
  api = installFakeApi();
  setToken(signIn(api));
  done.mockReset();
  openHelp.mockReset();
});
afterEach(() => {
  vi.useRealTimers();
  api.restore();
  vi.unstubAllGlobals();
});

function Shell() {
  const context: AppContext = { openHelp, reportFailure: () => false };
  return <Outlet context={context} />;
}

function mountRoom() {
  return render(
    <MemoryRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<RoleplayRoom lessonId="m1_l1" context="lesson" onDone={done} />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

const turnCalls = () => api.calls.filter((c) => /\/roleplay\/[^/]+\/turn$/.test(c.path));
const box = () => screen.findByRole("textbox", { name: "What would you say?" });

async function typeAndSend(text: string) {
  const user = userEvent.setup();
  await user.type(await box(), text);
  await user.click(screen.getByRole("button", { name: "Send" }));
  return user;
}

describe("role-play safety", () => {
  it("crisis stops the run: input removed, resources tappable, no more turn calls", async () => {
    api.scenario.roleplayMode = ["crisis"];
    const { container } = mountRoom();
    const user = await typeAndSend("a private worry");
    expect(await screen.findByRole("heading", { name: "Let's pause the practice" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button", { name: "Send" })).toBeNull();
    expect(screen.queryByText("a private worry")).toBeNull();
    expect(screen.getByRole("link", { name: /Call 988 Suicide & Crisis Lifeline at 988/ })).toHaveAttribute(
      "href",
      "tel:988",
    );
    expect(screen.getByRole("link", { name: /Alzheimer's Association 24\/7 Helpline/ })).toHaveAttribute(
      "href",
      "tel:18002723900",
    );
    expect(screen.queryByRole("button", { name: "Keep practicing" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Need help now?" }));
    expect(openHelp).toHaveBeenCalledTimes(1);
    expect(turnCalls()).toHaveLength(1);
    expect(await axe(container)).toHaveNoViolations();
    await user.click(screen.getByRole("button", { name: "Leave practice" }));
    expect(done).toHaveBeenCalledWith(null);
  });

  it("emergency shows the server text with a 911 link and can continue", async () => {
    api.scenario.roleplayMode = ["emergency", "ai"];
    mountRoom();
    const user = await typeAndSend("she fell");
    expect(await screen.findAllByText("If this is happening now, call 911.")).not.toHaveLength(0);
    expect(screen.getByRole("heading", { name: "If this is happening now" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Emergency services at 911/ })).toHaveAttribute("href", "tel:911");
    expect(screen.queryByRole("textbox")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Keep practicing" }));
    expect(await box()).toHaveValue("");
    expect(screen.getByText("Round 1 of 3")).toBeInTheDocument();
  });

  it("shows the fixed medical tip and score 0 exactly as the server sent them", async () => {
    api.scenario.roleplayMode = ["medical"];
    mountRoom();
    await typeAndSend("should she take more pills");
    expect(await screen.findByText(/ask Mom's doctor or pharmacist/)).toBeInTheDocument();
    expect(screen.getByText(/0 of 3/)).toBeInTheDocument();
    expect(screen.queryByText("Try:")).toBeNull();
  });
});

describe("role-play fallback and failures", () => {
  it("switches to multiple choice and stays there; no turn input or call after that", async () => {
    api.scenario.roleplayMode = ["fallback", "ai"];
    const { container } = mountRoom();
    const user = await typeAndSend("hello");
    expect(await screen.findByText(/The practice partner isn't available right now/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByText("Choice 1 of 2. Pick the answer you would say.")).toBeInTheDocument();
    expect(container.textContent).not.toContain("{");
    await user.click(screen.getByRole("button", { name: /Why do you keep asking/ }));
    expect(screen.getByText(/It can feel like blame/)).toBeInTheDocument();
    expect(screen.getByText("Try again")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /You sound worried/ }));
    expect(screen.getByText("Best")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Choice 2 of 2. Pick the answer you would say.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /It sounds like you feel left out/ }));
    expect(await axe(container)).toHaveNoViolations();
    await user.click(screen.getByRole("button", { name: "Finish practice" }));
    expect(await screen.findByRole("heading", { name: "Nicely done" })).toBeInTheDocument();
    expect(turnCalls()).toHaveLength(1);
    expect(api.calls.some((c) => c.path.endsWith("/finish"))).toBe(true);
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(done).toHaveBeenCalledWith(expect.objectContaining({ mode: "fallback" }));
  });

  it("a timeout shows the retry state within 15 s and a retry returns fallback scenarios", async () => {
    const real = globalThis.fetch;
    let hung = false;
    vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (!hung && /\/roleplay\/[^/]+\/turn$/.test(url)) {
        hung = true;
        return new Promise<Response>((_, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        });
      }
      return real(input, init);
    });
    api.scenario.roleplayMode = ["fallback"];
    mountRoom();
    fireEvent.change(await box(), { target: { value: "hello" } });
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await vi.advanceTimersByTimeAsync(15_000);
    vi.useRealTimers();
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText(/The practice partner isn't available right now/)).toBeInTheDocument();
    expect(within(alert).getByRole("button", { name: "Skip practice" })).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toHaveValue("hello");
    fireEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Choice 1 of 2. Pick the answer you would say.")).toBeInTheDocument();
  });

  it("start failure (429) shows the aiDown line with Try again and Skip practice", async () => {
    api.injectError("POST", "/roleplay/start", 429, "rate_limited");
    mountRoom();
    expect(await screen.findByText(/The practice partner isn't available right now/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Skip practice" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await box()).toBeInTheDocument();
  });

  it("keeps reply text out of storage and the console", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((k) => vi.spyOn(console, k));
    api.scenario.roleplayMode = ["crisis"];
    mountRoom();
    await typeAndSend("zebra-secret-phrase");
    await screen.findByRole("heading", { name: "Let's pause the practice" });
    const stored = JSON.stringify([...Object.entries(window.localStorage), ...Object.entries(window.sessionStorage)]);
    expect(stored).not.toContain("zebra-secret-phrase");
    for (const spy of spies) expect(JSON.stringify(spy.mock.calls)).not.toContain("zebra-secret-phrase");
    spies.forEach((s) => s.mockRestore());
  });
});

describe("practice round page", () => {
  it("runs from the Today card with context practice_round and returns to Today", async () => {
    api.scenario.today = "day2";
    const { container } = render(
      <MemoryRouter initialEntries={["/today"]}>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/today" element={<WithAppCopy><TodayPage /></WithAppCopy>} />
            <Route path="/today/practice" element={<PracticeRoundPage />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("link", { name: "Start practice" }));
    expect(await screen.findByRole("heading", { level: 1, name: "2-minute practice" })).toBeInTheDocument();
    await screen.findByText("Round 1 of 2");
    const startCall = vi.mocked(fetch).mock.calls.find(([url]) => String(url).endsWith("/roleplay/start"));
    expect(JSON.parse(String(startCall?.[1]?.body))).toMatchObject({ context: "practice_round" });
    expect(await axe(container)).toHaveNoViolations();
    await user.type(await box(), "I'm here.");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("AI-generated");
    await user.click(screen.getByRole("button", { name: "Next round" }));
    await screen.findByText("Round 2 of 2");
    await user.type(await box(), "Let's sit.");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("AI-generated");
    await user.click(screen.getByRole("button", { name: "See your practice" }));
    await screen.findByRole("heading", { name: "Your practice" });
    const todayCalls = () => api.calls.filter((c) => c.path === "/today").length;
    const before = todayCalls();
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByRole("heading", { level: 1, name: /^Today with /i });
    await waitFor(() => expect(todayCalls()).toBeGreaterThan(before));
  });

  it("says so when Today offers no practice round", async () => {
    api.scenario.today = "fresh";
    render(
      <MemoryRouter initialEntries={["/today/practice"]}>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/today/practice" element={<PracticeRoundPage />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "No practice right now" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Today" })).toHaveAttribute("href", "/today");
  });
});
