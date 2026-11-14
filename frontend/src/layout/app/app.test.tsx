import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { ESLint } from "eslint";
import { resolve } from "node:path";
import { createMemoryRouter, RouterProvider, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { crisisStore } from "../../api/useCrisisResources";
import { routes } from "../../router";
import { AppLayout } from "./AppLayout";
import { useAppContext } from "./appContext";
import { DESKTOP_QUERY } from "./useIsDesktop";

// jsdom's AbortSignal is rejected by Node's Request, which React Router builds on navigation.
const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

const fetchMock = vi.fn<typeof fetch>();

// Shape of GET /app-copy `nav` (backend schemas/app_copy.py NavCopyOut), values as served for "Mom".
const APP_COPY = {
  nav: {
    today: "Today",
    plan: "Plan",
    profilePage: "Mom’s page",
    skills: "Skills",
    settings: "Settings",
  },
};

type Reply = { status: number; body: unknown };
let appCopyReply: Reply;

const json = (status: number, body: unknown): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const error = (status: number, code: string, details: unknown = {}): Reply => ({
  status,
  body: { error: { code, message: "Server says so.", details } },
});

function setDesktop(on: boolean): void {
  vi.stubGlobal(
    "matchMedia",
    (query: string): MediaQueryList =>
      ({
        matches: on && query === DESKTOP_QUERY,
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList,
  );
}

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  crisisStore.reset();
  appCopyReply = { status: 200, body: APP_COPY };
  fetchMock.mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/api/app-copy"))
      return Promise.resolve(json(appCopyReply.status, appCopyReply.body));
    return Promise.resolve(
      json(200, {
        verifyBeforeLaunch: true,
        resources: [
          {
            id: "a",
            name: "Test Line",
            phone: "1-800-000-1111",
            description: "From the API.",
          },
        ],
      }),
    );
  });
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  setDesktop(false);
});
afterEach(() => vi.unstubAllGlobals());

function LocationProbe() {
  const { pathname, state } = useLocation();
  return (
    <p
      data-testid="loc"
      data-restore={String(
        (state as { restore?: boolean } | null)?.restore === true,
      )}
    >
      {pathname}
    </p>
  );
}

async function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const utils = render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { level: 1 });
  return { router, ...utils };
}

const APP_ROUTES: [string, string][] = [
  ["/today", "Today is coming soon"],
  ["/today/practice", "Practice round"],
  ["/lessons/m1_l1", "Lesson"],
  ["/plan", "Plan"],
  ["/profile", "Profile"],
  ["/care-card", "Care card"],
  ["/visit-sheet", "Visit sheet"],
  ["/skills", "Skills"],
  ["/settings", "Settings"],
  ["/settings/cancel", "Cancel subscription"],
  ["/settings/gentle-exit", "Gentle exit"],
];

describe("app routes", () => {
  it.each(APP_ROUTES)(
    "%s renders inside the app shell with one main and one nav",
    async (path, h1) => {
      await renderAt(path);
      expect(
        screen.getByRole("heading", { level: 1, name: h1 }),
      ).toBeInTheDocument();
      expect(screen.getAllByRole("main")).toHaveLength(1);
      const navs = screen.queryAllByRole("navigation", { name: "App" });
      expect(navs).toHaveLength(
        path.startsWith("/lessons") || path === "/today/practice" ? 0 : 1,
      );
      expect(
        document.head.querySelector('meta[name="robots"][content="noindex"]'),
      ).not.toBeNull();
      // Stubs fetch nothing of their own: only the shell's app-copy and the help sheet's crisis list.
      const urls = fetchMock.mock.calls.map(([u]) => String(u));
      expect(
        urls.filter(
          (u) =>
            !u.includes("/api/app-copy") &&
            !u.includes("/api/resources/crisis"),
        ),
      ).toEqual([]);
    },
  );

  it("renders the public card outside the app shell, without a session request", async () => {
    await renderAt("/card/abc");
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(
      fetchMock.mock.calls.filter(([u]) => String(u).includes("/api/app-copy")),
    ).toHaveLength(0);
  });

  it("renders /goodbye outside the app shell", async () => {
    await renderAt("/goodbye");
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(
      fetchMock.mock.calls.filter(([u]) => String(u).includes("/api/app-copy")),
    ).toHaveLength(0);
  });

  it("still shows the 404 for an unknown URL", async () => {
    await renderAt("/nope/nothing");
    expect(
      screen.getByRole("heading", { level: 1, name: /can’t find that page/ }),
    ).toBeInTheDocument();
  });
});

describe("layouts", () => {
  it("uses the top bar and a four-tab bar below 1024px", async () => {
    await renderAt("/plan");
    const tabs = screen.getByRole("navigation", { name: "App" });
    expect(tabs).toHaveAttribute("data-app-chrome", "tab-bar");
    expect(
      within(tabs)
        .getAllByRole("link")
        .map((a) => a.textContent),
    ).toEqual(["Today", "Plan", "Mom’s page", "Skills"]);
    const top = screen.getByRole("banner");
    expect(
      within(top).getByRole("link", { name: "Settings" }),
    ).toBeInTheDocument();
    expect(
      within(top).getByRole("button", { name: "Need help now?" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("complementary")).toBeNull();
  });

  it("uses the sidebar at 1024px and up, with Settings and the disclaimer, and no tab bar or top bar", async () => {
    setDesktop(true);
    await renderAt("/plan");
    const side = screen.getByRole("complementary");
    const nav = within(side).getByRole("navigation", { name: "App" });
    expect(
      within(nav)
        .getAllByRole("link")
        .map((a) => a.textContent),
    ).toEqual(["Today", "Plan", "Mom’s page", "Skills", "Settings"]);
    expect(
      within(side).getByRole("button", { name: "Need help now?" }),
    ).toBeInTheDocument();
    expect(
      within(side).getByText(/don’t give medical advice/),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("navigation")).toHaveLength(1);
    expect(screen.queryByRole("banner")).toBeNull();
  });

  it("follows the route with aria-current (lesson and visit sheet keep Today lit)", async () => {
    const { router } = await renderAt("/plan");
    const current = () =>
      within(screen.getByRole("navigation", { name: "App" }))
        .queryAllByRole("link")
        .filter((a) => a.getAttribute("aria-current") === "page")
        .map((a) => a.textContent);
    expect(current()).toEqual(["Plan"]);
    await act(async () => {
      await router.navigate("/visit-sheet");
    });
    await screen.findByRole("heading", { level: 1, name: "Visit sheet" });
    expect(current()).toEqual(["Today"]);
    await act(async () => {
      await router.navigate("/care-card");
    });
    await screen.findByRole("heading", { level: 1, name: "Care card" });
    expect(current()).toEqual(["Mom’s page"]);
    await act(async () => {
      await router.navigate("/settings/cancel");
    });
    await screen.findByRole("heading", {
      level: 1,
      name: "Cancel subscription",
    });
    expect(current()).toEqual([]);
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("hides the tab bar and the top bar links on the lesson route, keeping Help", async () => {
    await renderAt("/lessons/m1_l1");
    expect(screen.queryByRole("navigation")).toBeNull();
    const top = screen.getByRole("banner");
    expect(within(top).queryAllByRole("link")).toHaveLength(0);
    expect(
      within(top).getByRole("button", { name: "Need help now?" }),
    ).toBeInTheDocument();
  });

  it("keeps the sidebar on the lesson route at 1024px and up, with Today lit", async () => {
    setDesktop(true);
    await renderAt("/lessons/m1_l1");
    const nav = screen.getByRole("navigation", { name: "App" });
    expect(within(nav).getByRole("link", { name: "Today" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("is axe clean in both layouts", async () => {
    const mobile = await renderAt("/plan");
    expect(await axe(mobile.container)).toHaveNoViolations();
    mobile.unmount();
    setDesktop(true);
    const desktop = await renderAt("/plan");
    expect(await axe(desktop.container)).toHaveNoViolations();
  });
});

describe("help, skip link and focus", () => {
  it.each(APP_ROUTES.map(([p]) => p))(
    "opens help from %s and returns focus",
    async (path) => {
      const user = userEvent.setup();
      await renderAt(path);
      const trigger = screen.getByRole("button", { name: "Need help now?" });
      await user.click(trigger);
      const dialog = await screen.findByRole("dialog", {
        name: "Need help now?",
      });
      expect(
        await within(dialog).findByRole("link", { name: /Test Line/ }),
      ).toBeInTheDocument();
      await act(async () => {
        (dialog as HTMLDialogElement).close();
      });
      expect(trigger).toHaveFocus();
    },
  );

  it("opens help from the desktop sidebar", async () => {
    setDesktop(true);
    const user = userEvent.setup();
    await renderAt("/skills");
    await user.click(screen.getByRole("button", { name: "Need help now?" }));
    expect(
      await screen.findByRole("dialog", { name: "Need help now?" }),
    ).toBeInTheDocument();
  });

  it("skip link moves focus to main", async () => {
    const user = userEvent.setup();
    await renderAt("/plan");
    await user.tab();
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
  });

  it("moves focus to the page h1 after navigation, and scrolls to the top", async () => {
    const user = userEvent.setup();
    await renderAt("/plan");
    expect(document.body).toHaveFocus();
    await user.click(screen.getByRole("link", { name: "Skills" }));
    const h1 = await screen.findByRole("heading", { level: 1, name: "Skills" });
    await waitFor(() => expect(h1).toHaveFocus());
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });
});

describe("gate handling", () => {
  it("sends a lost session (401) to /quiz with the restore state", async () => {
    appCopyReply = error(401, "invalid_session_token");
    const router = createMemoryRouter(
      [
        ...routes,
        // Observe where the shell sends the visitor: swap /quiz for a probe.
      ].map((r) => r),
      { initialEntries: ["/plan"] },
    );
    render(<RouterProvider router={router} />);
    await waitFor(() => expect(router.state.location.pathname).toBe("/quiz"));
    expect(
      (router.state.location.state as { restore?: boolean } | null)?.restore,
    ).toBe(true);
  });

  it("sends no_subscription to /paywall and ended to /", async () => {
    appCopyReply = error(402, "payment_required", {
      reason: "no_subscription",
    });
    const a = createMemoryRouter(routes, { initialEntries: ["/plan"] });
    const first = render(<RouterProvider router={a} />);
    await waitFor(() => expect(a.state.location.pathname).toBe("/paywall"));
    first.unmount();

    appCopyReply = error(402, "payment_required", { reason: "ended" });
    const b = createMemoryRouter(routes, { initialEntries: ["/plan"] });
    render(<RouterProvider router={b} />);
    await waitFor(() => expect(b.state.location.pathname).toBe("/"));
  });

  it("shows a retry state when the nav copy fails with a server error", async () => {
    const user = userEvent.setup();
    appCopyReply = error(500, "internal_error");
    const router = createMemoryRouter(routes, { initialEntries: ["/plan"] });
    render(<RouterProvider router={router} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We could not load",
    );
    expect(
      screen.getByRole("button", { name: "Need help now?" }),
    ).toBeInTheDocument();
    appCopyReply = { status: 200, body: APP_COPY };
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Plan" }),
    ).toBeInTheDocument();
  });

  function Reporter() {
    const { reportFailure } = useAppContext();
    return (
      <>
        <h1 data-app-heading tabIndex={-1}>
          Reporter
        </h1>
        <button
          type="button"
          onClick={() =>
            reportFailure(
              { kind: "gate", reason: "past_due" },
              "Your card was declined.",
            )
          }
        >
          Report past due
        </button>
        <button
          type="button"
          onClick={() =>
            reportFailure({ kind: "gate", reason: "no_subscription" })
          }
        >
          Report no subscription
        </button>
        <LocationProbe />
      </>
    );
  }
  const reporterRoutes = [
    {
      element: <AppLayout />,
      children: [{ path: "/r", element: <Reporter /> }],
    },
    { path: "/paywall", element: <h1>Paywall</h1> },
  ];

  it("shows PastDueNotice with a Settings link and keeps the shell usable on past_due", async () => {
    const user = userEvent.setup();
    const router = createMemoryRouter(reporterRoutes, {
      initialEntries: ["/r"],
    });
    render(<RouterProvider router={router} />);
    await user.click(
      await screen.findByRole("button", { name: "Report past due" }),
    );
    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("Your card was declined.");
    expect(
      within(notice).getByRole("link", { name: "Settings" }),
    ).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("navigation", { name: "App" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Need help now?" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/r");
  });

  it("redirects a page-level no_subscription to /paywall", async () => {
    const user = userEvent.setup();
    const router = createMemoryRouter(reporterRoutes, {
      initialEntries: ["/r"],
    });
    render(<RouterProvider router={router} />);
    await user.click(
      await screen.findByRole("button", { name: "Report no subscription" }),
    );
    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/paywall"),
    );
  });
});

describe("styles", () => {
  const read = (f: string): string =>
    readFileSync(new URL(f, import.meta.url), "utf8");

  it("switches layout at min-width 1024px in the code and the CSS", () => {
    expect(DESKTOP_QUERY).toBe("(min-width: 1024px)");
    expect(read("./AppLayout.module.css")).toContain(
      "@media (min-width: 1024px)",
    );
  });

  it("keeps tab bar targets at 48px, safe-area aware, with scroll padding", () => {
    const css = read("./AppChrome.module.css");
    expect(css).toMatch(/\.tab \{[^}]*min-height: var\(--tap-min\)/);
    expect(css).toMatch(
      /\.tabBar \{[^}]*height: calc\(\s*var\(--tabbar-h\) \+ env\(safe-area-inset-bottom/,
    );
    expect(css).toMatch(/\.help \{[^}]*min-height: var\(--tap-min\)/);
    expect(read("./AppLayout.module.css")).toMatch(
      /\.rootPadding \{[^}]*scroll-padding-bottom: calc\(\s*var\(--tabbar-h\)/,
    );
  });

  it("hides the chrome in print and sets a Letter page", () => {
    const css = read("./AppLayout.module.css");
    expect(css).toMatch(/@page \{[^}]*size: Letter/);
    expect(css).toMatch(
      /@media print \{[^}]*\[data-app-chrome\] \{[^}]*display: none/,
    );
  });
});

describe("lint rule", () => {
  it("rejects an api import from src/components", async () => {
    const eslint = new ESLint();
    const [result] = await eslint.lintText(
      'import { apiGet } from "../../api/client";\nexport const x = apiGet;\n',
      {
        filePath: resolve(process.cwd(), "src/components/app/Probe.ts"),
      },
    );
    expect(result?.messages.map((m) => m.message)).toEqual([
      expect.stringContaining("restricted"),
    ]);
  });
});
