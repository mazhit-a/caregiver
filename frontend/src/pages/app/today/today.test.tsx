import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter, Outlet, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import type { AppContext } from "../../../layout/app/appContext";
import { clearToken, setToken } from "../../../api/session";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import type { TodayState } from "../../../test/fakeApp/registry";
import TodayPage from "../TodayPage";
import { WithAppCopy } from "../../../test/withAppCopy";

let api: FakeApi;
const report = vi.fn<AppContext["reportFailure"]>();

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

beforeEach(() => {
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  clearToken();
  report.mockReset();
  report.mockReturnValue(true);
  api = installFakeApi();
  setToken(signIn(api));
});
afterEach(() => api.restore());

function Shell() {
  const context: AppContext = { openHelp: () => undefined, reportFailure: report };
  return <Outlet context={context} />;
}

function renderToday() {
  return render(
    <MemoryRouter initialEntries={["/today"]}>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/today" element={<WithAppCopy><TodayPage /></WithAppCopy>} />
          <Route path="*" element={<p>elsewhere</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

async function ready(state: TodayState) {
  api.scenario.today = state;
  const view = renderToday();
  await screen.findByRole("heading", { level: 1, name: /^Today with /i });
  return view;
}

const sectionHeadings = () =>
  screen
    .getAllByRole("heading", { level: 2 })
    .map((h) => h.textContent)
    .filter((t) => t !== "Welcome");

describe("TodayPage", () => {
  it("fresh: Start lesson links to the first lesson, and the sections follow the API order", async () => {
    await ready("fresh");
    const cta = screen.getByRole("link", { name: "Start lesson" });
    expect(cta).toHaveAttribute("href", "/lessons/m1_l1");
    expect(screen.getByText(/Today's step · 8 min · Communication/)).toBeInTheDocument();
    expect(sectionHeadings()).toEqual(["When Mom asks again", "This week", "Your plan"]);
    expect(screen.getByText("Mom's plan: 0 of 12 lessons done")).toBeInTheDocument();
    expect(screen.getByText("This week: 0 of 4 practice sessions.")).toBeInTheDocument();
    expect(screen.getByText("Your plan renews on February 2.")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Your plan" })).toHaveAttribute(
      "aria-valuetext",
      "0 of 12",
    );
  });

  it("day2: rest message, unlock text and no lesson button; practice round links to the practice page", async () => {
    await ready("day2");
    expect(screen.getByText("You're done for today. Rest counts too.")).toBeInTheDocument();
    expect(screen.getByText("Your next lesson opens on January 7.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /lesson/i })).toBeNull();
    const practice = screen.getByRole("link", { name: "Start practice" });
    expect(practice).toHaveAttribute("href", "/today/practice");
    expect(screen.getByText("2-minute practice: a new version")).toBeInTheDocument();
  });

  it("nudge: shows the server text and links to the care card", async () => {
    await ready("nudge");
    expect(screen.getByText(/Your care card has 1 new phrase\. Update it\?/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Update card" })).toHaveAttribute("href", "/care-card");
  });

  it("all_done: shows the server message", async () => {
    await ready("all_done");
    expect(screen.queryByRole("link", { name: /lesson/i })).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: /finished|done|rest/i })).toBeInTheDocument();
  });

  it("renders the order the API sends, ignores unknown sections, shows welcome back", async () => {
    api.inject({
      method: "GET",
      path: "/today",
      status: 200,
      body: {
        title: "Today with Mom",
        order: ["readiness", "mystery", "welcomeBack", "nextStep"],
        checkIn: null,
        practiceRound: null,
        careCardNudge: null,
        nextStep: { kind: "rest", message: "Rest counts too.", lesson: null, unlockText: null },
        weeklyRhythm: { done: 1, target: 4, text: "This week: 1 of 4 practice sessions." },
        readiness: { done: 2, total: 12, text: "Mom's plan: 2 of 12 lessons done" },
        subscriptionNotice: null,
        welcomeBack: { title: "Welcome back", body: "Pick up whenever you're ready." },
        visitSheetLink: { label: "Prepare for a doctor visit", path: "/api/visit-sheet" },
        demo: null,
      },
    });
    renderToday();
    await screen.findByRole("heading", { level: 1, name: "Today with Mom" });
    expect(sectionHeadings()).toEqual(["Your plan", "Welcome back", "Rest counts too."]);
    expect(
      screen.getByRole("link", { name: "Prepare for a doctor visit" }),
    ).toHaveAttribute("href", "/visit-sheet");
  });

  it("shows no unfilled placeholder in any state", async () => {
    for (const state of ["fresh", "day2", "nudge", "all_done"] as const) {
      const { unmount } = await ready(state);
      expect(document.body.textContent ?? "").not.toMatch(/[{}]/);
      unmount();
    }
  });

  it("loads, fails with retry, then recovers", async () => {
    const user = userEvent.setup();
    api.injectError("GET", "/today", 500, "internal_error");
    renderToday();
    expect(screen.getByRole("status")).toBeInTheDocument();
    const alert = await screen.findByRole("alert");
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { level: 1, name: /^Today with /i });
  });

  it("a 402 is handed to the shell and the page renders nothing", async () => {
    api.injectError("GET", "/today", 402, "payment_required", { reason: "no_subscription" });
    renderToday();
    await waitFor(() => expect(report).toHaveBeenCalled());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("a demo control press refetches Today silently: the page and the demo status stay mounted", async () => {
    const user = userEvent.setup();
    await ready("fresh");
    const h1 = screen.getByRole("heading", { level: 1, name: /^Today with /i });
    const before = api.calls.filter((c) => c.path === "/today").length;
    await user.click(screen.getByRole("button", { name: "Simulate next day (demo)" }));
    await waitFor(() => expect(api.calls.filter((c) => c.path === "/today").length).toBe(before + 1));
    expect(await screen.findByText("Day moved forward")).toBeInTheDocument();
    expect(h1.isConnected).toBe(true);
    expect(screen.queryByText(/Loading/i)).toBeNull();
  });

  it("refetches on mount (reload)", async () => {
    const first = await ready("fresh");
    first.unmount();
    await ready("fresh");
    expect(api.calls.filter((c) => c.path === "/today").length).toBe(2);
  });

  it.each(["fresh", "day2", "nudge", "all_done"] as const)("%s has no axe violations", async (state) => {
    const { container } = await ready(state);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("does the page do no date arithmetic (source check)", () => {
    for (const file of ["../TodayPage.tsx", "sections.tsx"]) {
      const src = readFileSync(resolve(__dirname, file), "utf-8");
      expect(src).not.toMatch(/new Date|Date\.now|getTime/);
    }
  });
});
