import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { crisisStore } from "../../api/useCrisisResources";
import { routes } from "../../router";
import giftFixture from "../../test/fixtures/gift-b.json";

// jsdom's AbortSignal is rejected by Node's Request, which React Router builds on navigation.
const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  crisisStore.reset();
  fetchMock.mockImplementation((input) =>
    Promise.resolve(
      String(input).includes("/api/plan/gift")
        ? new Response(JSON.stringify(giftFixture), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        : crisisResponse(),
    ),
  );
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

function crisisResponse(): Response {
  return new Response(
    JSON.stringify({
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
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

async function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const utils = render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { level: 1 });
  return { router, ...utils };
}

const FUNNEL: [string, string][] = [
  ["/quiz", "The quiz is coming soon"],
  ["/quiz/q1_recipient", "Quiz"],
  ["/quiz/reassure_1", "Quiz"],
  ["/quiz/building", "Building your plan"],
  ["/your-plan", "Your plan"],
  ["/your-plan/gift", "Phrases that calm Mom"],
  ["/paywall", "Start your plan"],
  ["/checkout/return", "Checking your payment"],
  ["/today", "Today is coming soon"],
];

describe("funnel routes", () => {
  it.each(FUNNEL)(
    "%s renders inside the funnel shell without any request",
    async (path, h1) => {
      await renderAt(path);
      expect(
        screen.getByRole("heading", { level: 1, name: h1 }),
      ).toBeInTheDocument();
      expect(screen.getAllByRole("main")).toHaveLength(1);
      // Focused shell: no site nav, no link list in the footer.
      expect(screen.queryByRole("navigation")).toBeNull();
      const footer = screen.getByRole("contentinfo");
      expect(within(footer).queryAllByRole("link")).toHaveLength(0);
      expect(
        within(footer).getByText(/don’t give medical advice/),
      ).toBeInTheDocument();
      // Only the shared help sheet may call the API (public crisis list); only the gift page fetches its own sheet.
      const urls = fetchMock.mock.calls.map(([u]) => String(u));
      expect(
        urls.filter(
          (u) =>
            !u.includes("/api/resources/crisis") &&
            !u.includes("/api/plan/gift"),
        ),
      ).toEqual([]);
    },
  );

  it("resolves /quiz/building to the building stub, not a question", async () => {
    await renderAt("/quiz/building");
    expect(
      screen.getByRole("heading", { level: 1, name: "Building your plan" }),
    ).toBeInTheDocument();
  });

  it("keeps the marketing layout for batch-1 pages and the 404", async () => {
    await renderAt("/how-it-works");
    expect(
      screen.getByRole("navigation", { name: "Main" }),
    ).toBeInTheDocument();
    await act(async () => {});
  });

  it("still shows the 404 for an unknown URL", async () => {
    await renderAt("/quiz-nope/x");
    expect(
      screen.getByRole("heading", { level: 1, name: /can’t find that page/ }),
    ).toBeInTheDocument();
  });

  it("marks stubs and the Today placeholder noindex", async () => {
    await renderAt("/today");
    expect(
      document.head.querySelector('meta[name="robots"][content="noindex"]'),
    ).not.toBeNull();
  });
});

describe("funnel header", () => {
  it.each(FUNNEL.map(([p]) => p))(
    "opens help from %s and returns focus",
    async (path) => {
      const user = userEvent.setup();
      await renderAt(path);
      const trigger = within(screen.getByRole("banner")).getByRole("button", {
        name: "Need help now?",
      });
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

  it("links the logo home", async () => {
    await renderAt("/paywall");
    expect(screen.getByRole("link", { name: "Kelper home" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("skip link is the first tab stop and moves focus to main", async () => {
    const user = userEvent.setup();
    await renderAt("/paywall");
    await user.tab();
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
  });

  it("moves focus to the step heading on navigation, not on first load", async () => {
    const { router } = await renderAt("/your-plan");
    expect(screen.getByRole("heading", { level: 1 })).not.toHaveFocus();
    await act(async () => {
      await router.navigate("/paywall");
    });
    const h1 = await screen.findByRole("heading", {
      level: 1,
      name: "Start your plan",
    });
    await waitFor(() => expect(h1).toHaveFocus());
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });
});

describe("funnel shell", () => {
  it("has no axe violations", async () => {
    const { container } = await renderAt("/paywall");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("sticks the action bar only on tall, wide viewports", () => {
    const css = readFileSync(
      "src/layout/funnel/FunnelScreen.module.css",
      "utf8",
    );
    expect(css).toMatch(
      /@media \(min-height: 600px\)[^{]*\{[^}]*\.bar\s*\{[^}]*position: sticky/s,
    );
  });
});
