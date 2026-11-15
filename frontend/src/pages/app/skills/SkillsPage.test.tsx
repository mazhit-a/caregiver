import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../../../api/session";
import { CONFIDENCE_LABELS, CONFIDENCE_ORDER } from "../../../content/app/skills";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import { appFixture } from "../../../test/fakeApp/fixtures";
import SkillsPage from "./SkillsPage";

let api: FakeApi;
const report = vi.fn(() => true);

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
  api = installFakeApi();
  setToken(signIn(api));
  report.mockClear();
});
afterEach(() => api.restore());

function renderPage() {
  const router = createMemoryRouter(
    [
      {
        element: <Outlet context={{ reportFailure: report, openHelp: () => undefined }} />,
        children: [
          { path: "/skills", element: <SkillsPage /> },
          { path: "/lessons/:id", element: <p>lesson page</p> },
        ],
      },
    ],
    { initialEntries: ["/skills"] },
  );
  return render(<RouterProvider router={router} />);
}

const ready = () => screen.findByRole("heading", { level: 1, name: "Your skills" });

describe("Skills page", () => {
  it("fresh session: empty state, start rating and the next lesson link", async () => {
    const { container } = renderPage();
    await ready();
    expect(await screen.findByText("Practice in lesson 1 to see how your replies change.")).toBeInTheDocument();
    expect(screen.getByText("2 of 5")).toBeInTheDocument();
    const link = await screen.findByRole("link", { name: /Open lesson/ });
    expect(link).toHaveAttribute("href", "/lessons/m1_l1");
    expect(screen.queryByText(/Now/)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[{}]/);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("after a run: scores, scenario result, confidence rows and counts", async () => {
    const state = [...api.sessions.values()][0];
    (state?.app as Record<string, unknown>)["ranRoleplay"] = true;
    const { container } = renderPage();
    await screen.findByRole("heading", { level: 2, name: "Communication" });
    expect(screen.getByText("First try: 3 of 3 (1 round)")).toBeInTheDocument();
    expect(screen.getByText("Best answer chosen in 1 of 1 scenario")).toBeInTheDocument();
    const repeat = screen.getByText("Repeated questions").closest("li") as HTMLElement;
    expect(within(repeat).getByText("3 of 5")).toBeInTheDocument();
    expect(screen.getByText("Getting what you need from a doctor visit")).toBeInTheDocument();
    expect(screen.getByText("Phrases saved").nextSibling).toHaveTextContent("1");
    // Next lesson is locked: server date, no link
    expect(screen.queryByRole("link", { name: /Open lesson/ })).not.toBeInTheDocument();
    expect(screen.getByText("Opens Jan 7")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[{}]/);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("shows the Now row only when latest exists, and two-round scores as first and latest", async () => {
    const base = appFixture("skills-full") as ReturnType<typeof appFixture> & Record<string, unknown>;
    const body = structuredClone(base) as unknown as {
      skills: { roleplay: { firstScore: number; latestScore: number } }[];
      confidence: { latest: Record<string, number> | null };
    };
    const roleplay = body.skills[0]?.roleplay;
    if (!roleplay) throw new Error("fixture changed");
    roleplay.firstScore = 1;
    roleplay.latestScore = 3;
    body.confidence.latest = { repeat: 4 };
    api.inject({ method: "GET", path: "/skills", status: 200, body, times: 1 });
    renderPage();
    await ready();
    expect(await screen.findByText("First try: 1 of 3. Latest: 3 of 3 (6 rounds)")).toBeInTheDocument();
    expect(screen.getByText("Now")).toBeInTheDocument();
    const repeat = screen.getByText("Repeated questions").closest("li") as HTMLElement;
    expect(within(repeat).getByText("4 of 5")).toBeInTheDocument();
    const other = screen.getByText("Upset evenings").closest("li") as HTMLElement;
    expect(within(other).queryByText("Now")).not.toBeInTheDocument();
  });

  it("shows loading, then an error with retry that works", async () => {
    api.injectError("GET", "/skills", 500, "server_error");
    renderPage();
    const alert = await screen.findByRole("alert");
    await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Next" })).toBeInTheDocument();
  });

  it("402 goes to the shell instead of the page", async () => {
    api.scenario.subscription = "past_due";
    renderPage();
    await waitFor(() => expect(report).toHaveBeenCalled());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("Skills contract", () => {
  it("confidence labels cover the wrap screen items of content/lessons/m1_l1.json", () => {
    const lesson = JSON.parse(readFileSync(resolve(process.cwd(), "../content/lessons/m1_l1.json"), "utf-8")) as {
      screens: { type: string; confidenceCheck?: { items: { id: string }[] } }[];
    };
    const ids = lesson.screens.find((s) => s.type === "wrap")?.confidenceCheck?.items.map((i) => i.id) ?? [];
    expect([...ids].sort()).toEqual([...CONFIDENCE_ORDER].sort());
    expect(Object.keys(CONFIDENCE_LABELS).sort()).toEqual([...ids].sort());
  });

  it("no stage, trend or score comparison is computed in the page source", () => {
    const src = readFileSync(resolve(process.cwd(), "src/pages/app/skills/SkillsPage.tsx"), "utf-8");
    expect(src).not.toMatch(/latestScore\s*[<>]|firstScore\s*[<>]|stage|trend/i);
  });
});
