import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { crisisStore } from "../api/useCrisisResources";
import { routes } from "../router";

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
  fetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        verifyBeforeLaunch: true,
        resources: [
          { id: "a", name: "Test Line", phone: "1-800-000-1111", description: "From the API." },
        ],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

async function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const utils = render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { level: 1 });
  return { router, ...utils };
}

const PAGES: [string, string][] = [
  ["/", "Kelper"],
  ["/how-it-works", "How it works"],
  ["/practice", "Practice with Ollie"],
  ["/course", "The course"],
  ["/care-tools", "Care tools"],
  ["/pricing", "Pricing and safety"],
  ["/quiz", "The quiz is coming soon"],
];

describe("routes", () => {
  it.each(PAGES)("%s renders inside the layout", async (path, heading) => {
    await renderAt(path);
    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("sets title and description for a page", async () => {
    await renderAt("/pricing");
    await waitFor(() => expect(document.title).toBe("Pricing and safety | Kelper"));
    expect(document.head.querySelector('meta[name="description"]')).not.toBeNull();
  });

  it("shows the 404 with noindex for an unknown URL", async () => {
    await renderAt("/nope");
    expect(screen.getByRole("heading", { level: 1, name: /can’t find that page/ })).toBeInTheDocument();
    expect(document.head.querySelector('meta[name="robots"][content="noindex"]')).not.toBeNull();
  });

  it("marks only the current page in the main nav", async () => {
    await renderAt("/course");
    const nav = screen.getByRole("navigation", { name: "Main" });
    const current = within(nav).getAllByRole("link", { current: "page" });
    expect(current.map((l) => l.textContent)).toEqual(["The course"]);
  });

  it("points every Get Mom’s plan link at /quiz", async () => {
    await renderAt("/");
    const links = screen.getAllByRole("link", { name: /Get Mom’s plan/ });
    expect(links.length).toBeGreaterThan(0);
    links.forEach((l) => expect(l).toHaveAttribute("href", "/quiz"));
  });

  it("navigates with the nav and moves focus to main", async () => {
    const user = userEvent.setup();
    await renderAt("/");
    await user.click(within(screen.getByRole("navigation", { name: "Main" })).getByRole("link", { name: "Pricing" }));
    await screen.findByRole("heading", { level: 1, name: "Pricing and safety" });
    await waitFor(() => expect(screen.getByRole("main")).toHaveFocus());
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("opens and closes the mobile menu with aria-expanded", async () => {
    const user = userEvent.setup();
    await renderAt("/");
    const menu = screen.getByRole("button", { name: "Menu" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    await user.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    await user.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "false");
  });
});

describe("skip link", () => {
  it("is the first tab stop and moves focus to main", async () => {
    const user = userEvent.setup();
    await renderAt("/");
    await user.tab();
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
  });
});

describe("help sheet", () => {
  it.each(["/", "/care-tools", "/nope"])("opens from the header on %s, closes and returns focus", async (path) => {
    const user = userEvent.setup();
    await renderAt(path);
    const trigger = within(screen.getByRole("banner")).getByRole("button", { name: "Need help now?" });
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "Need help now?" });
    expect(await within(dialog).findByRole("link", { name: /Test Line/ })).toHaveAttribute(
      "href",
      "tel:1-800-000-1111".replace(/-/g, ""),
    );
    expect(within(dialog).getByText("We teach and organize. We don’t give medical advice.")).toBeInTheDocument();
    await act(async () => {
      (dialog as HTMLDialogElement).close();
    });
    expect(trigger).toHaveFocus();
  });

  it("falls back to the bundled numbers when the request fails", async () => {
    fetchMock.mockRejectedValue(new TypeError("offline"));
    const user = userEvent.setup();
    await renderAt("/");
    await user.click(within(screen.getByRole("banner")).getByRole("button", { name: "Need help now?" }));
    const dialog = await screen.findByRole("dialog", { name: "Need help now?" });
    await waitFor(() => expect(crisisStore.getSnapshot().status).toBe("error"));
    expect(within(dialog).getByText("911")).toBeInTheDocument();
    expect(within(dialog).getByText("988")).toBeInTheDocument();
    expect(within(dialog).getByText("1-800-272-3900")).toBeInTheDocument();
  });

  it("footer band shows the first three resources", async () => {
    await renderAt("/");
    const footer = screen.getByRole("contentinfo");
    await waitFor(() => expect(within(footer).getByText("1-800-000-1111")).toBeInTheDocument());
  });
});

describe("accessibility", () => {
  it("has no axe violations on layout + stub", async () => {
    const { container } = await renderAt("/how-it-works");
    expect(await axe(container)).toHaveNoViolations();
  });
});
