import { readFileSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { routes } from "../../router";
import gift from "../../test/fixtures/gift-b.json";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

const fetchMock = vi.fn<typeof fetch>();
const reply = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const onGift = (res: () => Response) =>
  fetchMock.mockImplementation((input) =>
    Promise.resolve(String(input).includes("/plan/gift") ? res() : reply(200, { resources: [] })),
  );

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => vi.unstubAllGlobals());

function renderGift() {
  const router = createMemoryRouter(routes, { initialEntries: ["/your-plan/gift"] });
  const utils = render(<RouterProvider router={router} />);
  return { router, ...utils };
}

describe("GiftPage", () => {
  it("renders the API sheet and prints on click", async () => {
    onGift(() => reply(200, gift));
    const print = vi.fn();
    vi.stubGlobal("print", print);
    const { container } = renderGift();
    expect(await screen.findByRole("heading", { level: 1, name: gift.title })).toBeTruthy();
    expect(screen.getByText(gift.intro)).toBeTruthy();
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    for (const p of gift.phrases) {
      expect(screen.getByText(p.text)).toBeTruthy();
      expect(screen.getByText(p.when)).toBeTruthy();
    }
    expect(screen.getAllByText(gift.footer).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/We teach and organize/).length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("{");
    await userEvent.click(screen.getByRole("button", { name: "Print or save as PDF" }));
    expect(print).toHaveBeenCalledTimes(1);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("shows an error with retry, and an empty sheet is an error", async () => {
    onGift(() => reply(500, { error: { code: "server_error", message: "x", details: {} } }));
    renderGift();
    expect(await screen.findByText("We couldn't load your sheet")).toBeTruthy();
    onGift(() => reply(200, { ...gift, phrases: [] }));
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([u]) => String(u).includes("/plan/gift"))).toHaveLength(2),
    );
    expect(await screen.findByText("We couldn't load your sheet")).toBeTruthy();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("routes a 402 by reason", async () => {
    onGift(() => reply(402, { error: { code: "payment_required", message: "x", details: { reason: "no_plan" } } }));
    const { router } = renderGift();
    await waitFor(() => expect(router.state.location.pathname).toBe("/quiz"));
  });

  it("print CSS hides chrome and buttons and sets Letter", () => {
    const css = readFileSync("src/pages/funnel/GiftPage.module.css", "utf8");
    const print = css.slice(css.indexOf("@media print"));
    expect(print).toMatch(/size:\s*Letter/);
    expect(print).toMatch(/margin:\s*0\.6in/);
    expect(print).toMatch(/header[\s\S]*footer[\s\S]*\.actions[\s\S]*display:\s*none/);
  });
});
