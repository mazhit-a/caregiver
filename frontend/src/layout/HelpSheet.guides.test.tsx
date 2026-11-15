import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { CRISIS_FALLBACK } from "../api/crisisFallback";
import { crisisStore } from "../api/useCrisisResources";
import { routes } from "../router";
import { installFakeApi, type FakeApi } from "../test/fakeApi";
import guideList from "../test/fixtures/guides/list.json";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

let api: FakeApi;

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
  crisisStore.reset();
  api = installFakeApi();
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

async function openSheet() {
  const router = createMemoryRouter(routes, { initialEntries: ["/guides/qg_fall"] });
  render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { level: 1, name: /fall/i });
  await userEvent.click(screen.getByRole("button", { name: "Need help now?" }));
  return router;
}

describe("help sheet quick guides", () => {
  it("lists the five guides as links and keeps the crisis numbers", async () => {
    await openSheet();
    const section = await screen.findByRole("region", { name: "Quick guides", hidden: true });
    const links = within(section).getAllByRole("link", { hidden: true });
    expect(links.map((l) => l.getAttribute("href"))).toEqual(guideList.guides.map((g) => `/guides/${g.id}`));
    expect(links.map((l) => l.textContent)).toEqual(guideList.guides.map((g) => g.title));
    expect(links).toHaveLength(5);
    for (const r of CRISIS_FALLBACK) expect(screen.getAllByText(r.phone, { exact: false }).length).toBeGreaterThan(0);
    expect(api.calls.filter((c) => c.path === "/guides").every((c) => c.token === null)).toBe(true);
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("a link opens the guide and closes the sheet", async () => {
    const router = await openSheet();
    const section = await screen.findByRole("region", { name: "Quick guides", hidden: true });
    await userEvent.click(within(section).getByRole("link", { name: guideList.guides[0]?.title ?? "", hidden: true }));
    expect(router.state.location.pathname).toBe(`/guides/${guideList.guides[0]?.id}`);
    expect(document.querySelector("dialog")?.hasAttribute("open")).toBe(false);
  });

  it("a failed guides request hides the list and never blocks the crisis numbers", async () => {
    api.injectError("GET", "/guides", 500, "server_error");
    await openSheet();
    for (const r of CRISIS_FALLBACK) expect(screen.getAllByText(r.phone, { exact: false }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("region", { name: "Quick guides", hidden: true })).toBeNull();
    expect(screen.queryByText("Quick guides")).toBeNull();
    expect(api.calls.some((c) => c.path === "/guides")).toBe(true);
  });
});
