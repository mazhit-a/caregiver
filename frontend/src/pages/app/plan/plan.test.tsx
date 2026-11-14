import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, Outlet, RouterProvider, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import type { CoursePlan, Today } from "../../../api/appTypes";
import type { PlanPreview } from "../../../api/funnelTypes";
import appCopy from "../../../test/fixtures/app/app-copy.json";
import planB from "../../../test/fixtures/app/plan.json";
import todayFresh from "../../../test/fixtures/app/today-fresh.json";
import previewA from "../../../test/fixtures/preview-a.json";
import previewB from "../../../test/fixtures/preview-b.json";
import previewC from "../../../test/fixtures/preview-c.json";
import PlanTabPage from "./PlanTabPage";
import { WithAppCopy } from "../../../test/withAppCopy";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}
const fetchMock = vi.fn<typeof fetch>();
const openHelp = vi.fn();
const reportFailure = vi.fn(() => false);

const json = (status: number, body: unknown): Response =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

interface Setup {
  plan: CoursePlan;
  preview: PlanPreview;
  today?: Today;
  failPlan?: { status: number; body: unknown };
}
let setup: Setup;

/** A course for a persona: the preview's module order, first lesson open, the rest by `inFirst30Days`. */
function planFromPreview(preview: PlanPreview): CoursePlan {
  return {
    heroLessonId: preview.firstLessonId,
    lessonsPerWeek: preview.pace.lessonsPerWeek,
    modules: preview.modules.map((m, mi) => ({
      id: m.id,
      title: m.title,
      reason: m.reason,
      lessons: m.lessons.map((l, li) => ({
        id: l.id,
        title: l.title,
        minutes: l.minutes,
        status: mi === 0 ? (li === 0 ? "available" : "locked") : "coming_later",
        unlockOn: mi === 0 ? `2026-01-0${5 + li}` : null,
      })),
    })),
  };
}

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  openHelp.mockReset();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  setup = {
    plan: structuredClone(planB) as CoursePlan,
    preview: structuredClone(previewB) as PlanPreview,
  };
  fetchMock.mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/api/app-copy")) return Promise.resolve(json(200, appCopy));
    if (url.includes("/api/today")) return Promise.resolve(json(200, setup.today ?? todayFresh));
    if (url.includes("/api/plan/preview")) return Promise.resolve(json(200, setup.preview));
    if (url.endsWith("/api/plan")) {
      return setup.failPlan
        ? Promise.resolve(json(setup.failPlan.status, setup.failPlan.body))
        : Promise.resolve(json(200, setup.plan));
    }
    return Promise.resolve(json(404, { error: { code: "not_found", message: "x", details: {} } }));
  });
});
afterEach(() => vi.unstubAllGlobals());

function must<T>(value: T | undefined | null): T {
  if (value === undefined || value === null) throw new Error("expected a value");
  return value;
}

function Where() {
  return <p data-testid="loc">{useLocation().pathname}</p>;
}

async function renderPlan() {
  const router = createMemoryRouter(
    [
      {
        element: <Outlet context={{ openHelp, reportFailure }} />,
        children: [
          { path: "/plan", element: <WithAppCopy><PlanTabPage /></WithAppCopy> },
          { path: "/lessons/:id", element: <Where /> },
        ],
      },
    ],
    { initialEntries: ["/plan"] },
  );
  const utils = render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { level: 1, name: "Mom's course" });
  return { router, ...utils };
}

describe("plan view: personas", () => {
  const personas: [string, PlanPreview][] = [
    ["A", previewA as PlanPreview],
    ["B", previewB as PlanPreview],
    ["C", previewC as PlanPreview],
  ];

  it.each(personas)("persona %s: modules, order and reasons come from the API", async (_n, preview) => {
    setup = { plan: planFromPreview(preview), preview };
    await renderPlan();
    const first = preview.modules.filter((m) => m.inFirst30Days);
    const later = preview.modules.filter((m) => !m.inFirst30Days);
    const shown = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(shown.slice(0, first.length)).toEqual(first.map((m) => m.title));
    const after = screen.getByRole("heading", { name: "After your first 30 days" });
    expect(after).toBeInTheDocument();
    for (const m of [...first, ...later]) expect(screen.getByText(m.reason)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/[{}]/);
  });

  it("persona B module 1 has 5 lessons with the fixture statuses; locked ones are not links", async () => {
    await renderPlan();
    const list = screen.getByRole("list", { name: "Talking with Mom" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(within(must(items[0])).getByRole("link")).toHaveAttribute("href", "/lessons/m1_l1");
    for (const item of items.slice(1)) expect(within(item).queryByRole("link")).toBeNull();
    expect(items[1]).toHaveTextContent("Opens Jan 7");
    expect(screen.getByText("Start")).toBeInTheDocument();
  });

  it("later modules read 'Coming later' without a padlock", async () => {
    await renderPlan();
    const card = must(screen.getByRole("heading", { name: "Caring for yourself" }).closest("li"));
    expect(card).toHaveTextContent("Coming later");
    expect(card.textContent).not.toMatch(/🔒|lock/i);
    expect(card.querySelector("svg")).toBeNull();
  });

  it("quick guides: highlight matches the fixture and only 'limit' is a button", async () => {
    const preview = previewC as PlanPreview;
    setup = { plan: planFromPreview(preview), preview };
    await renderPlan();
    const guides = screen.getByRole("region", { name: "Quick guides for urgent moments" });
    const highlighted = preview.quickGuides.filter((g) => g.highlight).map((g) => g.title);
    for (const g of preview.quickGuides) {
      const chip = within(guides).getByText(g.title, { exact: false });
      const marked = within(must(chip.closest("li"))).queryByText("For now") !== null;
      expect(marked, g.title).toBe(highlighted.includes(g.title));
    }
    expect(within(guides).getAllByRole("button")).toHaveLength(1);
    await userEvent.click(within(guides).getByRole("button", { name: /limit/ }));
    expect(openHelp).toHaveBeenCalledTimes(1);
    expect(within(guides).getByText(/still being written/)).toBeInTheDocument();
  });
});

describe("plan view: header, toggle, all modules", () => {
  it("shows the server progress text and a progressbar", async () => {
    await renderPlan();
    expect(screen.getByText("Mom's plan: 0 of 12 lessons done")).toBeInTheDocument();
    const bars = screen.getAllByRole("progressbar");
    expect(bars[0]).toHaveAttribute("aria-valuemax", "12");
  });

  it("the toggle keeps keyboard focus and switches the view", async () => {
    await renderPlan();
    const all = screen.getByRole("radio", { name: "All modules" });
    all.focus();
    await userEvent.keyboard(" ");
    expect(all).toBeChecked();
    expect(all).toHaveFocus();
    expect(screen.getAllByRole("progressbar").length).toBeGreaterThan(2);
    expect(screen.getByText("0 of 5 lessons done")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the first lesson/ })).toHaveAttribute(
      "href",
      "/lessons/m1_l1",
    );
  });

  it("a module with no open lesson jumps to the path and focuses its heading", async () => {
    await renderPlan();
    await userEvent.click(screen.getByRole("radio", { name: "All modules" }));
    await userEvent.click(screen.getByRole("button", { name: /See in the path\s*: Hard moments/ }));
    expect(screen.getByRole("radio", { name: "Path" })).toBeChecked();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Hard moments" })).toHaveFocus(),
    );
  });

  it("an open lesson link navigates to the lesson", async () => {
    const { router } = await renderPlan();
    await userEvent.click(screen.getByRole("link", { name: /When Mom asks again/ }));
    expect(router.state.location.pathname).toBe("/lessons/m1_l1");
  });

  it("done lessons are not links and show 'Done'", async () => {
    const plan = structuredClone(planB) as CoursePlan;
    must(must(plan.modules[0]).lessons[0]).status = "done";
    must(must(plan.modules[0]).lessons[1]).status = "available";
    setup.plan = plan;
    await renderPlan();
    const items = within(screen.getByRole("list", { name: "Talking with Mom" })).getAllByRole("listitem");
    expect(within(must(items[0])).queryByRole("link")).toBeNull();
    expect(items[0]).toHaveTextContent("Done");
    expect(within(must(items[1])).getByRole("link")).toBeInTheDocument();
    expect(screen.getByText("1 of 5 done")).toBeInTheDocument();
  });
});

describe("plan view: states and accessibility", () => {
  it("loading shows a status, then the course", async () => {
    const router = createMemoryRouter(
      [{ element: <Outlet context={{ openHelp, reportFailure }} />, children: [{ path: "/plan", element: <WithAppCopy><PlanTabPage /></WithAppCopy> }] }],
      { initialEntries: ["/plan"] },
    );
    render(<RouterProvider router={router} />);
    expect(await screen.findByRole("status")).toHaveTextContent("Loading course");
    await screen.findByRole("heading", { name: "Mom's course" });
  });

  it("an error shows a retry that reloads", async () => {
    setup.failPlan = { status: 500, body: { error: { code: "server", message: "x", details: {} } } };
    const router = createMemoryRouter(
      [{ element: <Outlet context={{ openHelp, reportFailure }} />, children: [{ path: "/plan", element: <WithAppCopy><PlanTabPage /></WithAppCopy> }] }],
      { initialEntries: ["/plan"] },
    );
    render(<RouterProvider router={router} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("We could not load the course");
    delete setup.failPlan;
    await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { name: "Mom's course" });
  });

  it("a 402 is reported to the shell and nothing is rendered", async () => {
    setup.failPlan = {
      status: 402,
      body: { error: { code: "payment_required", message: "x", details: { reason: "no_subscription" } } },
    };
    const router = createMemoryRouter(
      [{ element: <Outlet context={{ openHelp, reportFailure }} />, children: [{ path: "/plan", element: <WithAppCopy><PlanTabPage /></WithAppCopy> }] }],
      { initialEntries: ["/plan"] },
    );
    const { container } = render(<RouterProvider router={router} />);
    await waitFor(() => expect(reportFailure).toHaveBeenCalled());
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("is axe clean in both views", async () => {
    const { container } = await renderPlan();
    expect(await axe(container)).toHaveNoViolations();
    await userEvent.click(screen.getByRole("radio", { name: "All modules" }));
    expect(await axe(container)).toHaveNoViolations();
  });

  it("never prints fear, countdown or per-day copy", async () => {
    await renderPlan();
    expect(document.body.textContent).not.toMatch(
      /per day|\/day|limited time|hurry|don't miss|special offer|discount/i,
    );
  });
});
