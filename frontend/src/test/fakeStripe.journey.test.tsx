/* eslint-disable @typescript-eslint/no-non-null-assertion -- fixture lookups in tests */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { createSession } from "../api/funnel";
import { clearToken, getToken } from "../api/session";
import { TEST_CARDS } from "../content/fakeStripe";
import { routes } from "../router";
import { type FakeApi, installFakeApi, SIM_CHECKOUT_ID } from "./fakeApi";
import copy from "./fixtures/funnel-copy.json";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

const user = userEvent.setup({ delay: null });
let api: FakeApi;
let logged: string[];
let router: ReturnType<typeof createMemoryRouter>;
let setItem: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  clearToken();
  logged = [];
  for (const level of ["log", "info", "warn", "error", "debug"] as const) {
    vi.spyOn(console, level).mockImplementation((...args: unknown[]) => {
      logged.push(args.map(String).join(" "));
    });
  }
  setItem = vi.spyOn(Storage.prototype, "setItem");
});
afterEach(() => {
  api?.restore();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function startAtPaywall() {
  api = installFakeApi({ fakeStripe: true });
  await createSession();
  const state = api.sessions.get(getToken() ?? "");
  if (state) state.completed = true;
  router = createMemoryRouter(routes, { initialEntries: ["/paywall"] });
  render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { level: 1, name: copy.paywall.headline });
}

async function toFakeCheckout() {
  await user.click(screen.getByRole("button", { name: copy.paywall.plans[0]!.payButtonLabel }));
  await waitFor(() => expect(router.state.location.pathname).toBe(`/fake-checkout/${SIM_CHECKOUT_ID}`));
  await screen.findByRole("heading", { level: 1, name: "Pay with a test card" });
}

async function fill(card: string) {
  await user.type(screen.getByLabelText("Card number"), card);
  await user.type(screen.getByLabelText(/Expiry/), "12/34");
  await user.type(screen.getByLabelText("CVC"), "123");
}

const noCardLeaks = (card: string) => {
  const digits = card.replace(/\s/g, "");
  expect(logged.join("\n")).not.toContain(digits);
  expect(setItem.mock.calls.flat().join("\n")).not.toContain(digits);
  expect(window.location.href).not.toContain(digits);
};

describe("fake Stripe journey", () => {
  it("paywall -> simulated checkout -> 4242 -> return -> Today", async () => {
    await startAtPaywall();
    await toFakeCheckout();
    expect(screen.getByText("Simulated checkout. No real payment.")).toBeInTheDocument();
    expect(await axe(document.body)).toHaveNoViolations();
    await fill("4242 4242 4242 4242");
    await user.click(screen.getByRole("button", { name: /^Pay / }));
    expect(await screen.findByRole("heading", { level: 1, name: copy.paywall.states.success })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/checkout/return");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByRole("heading", { level: 1, name: /^Today/ });
    noCardLeaks("4242 4242 4242 4242");
  }, 30000);

  it("declined card shows the API message, stays on the page, and a retry with 4242 works", async () => {
    await startAtPaywall();
    await toFakeCheckout();
    await fill("4000 0000 0000 0002");
    await user.click(screen.getByRole("button", { name: /^Pay / }));
    expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("Your card was declined.");
    expect(router.state.location.pathname).toBe(`/fake-checkout/${SIM_CHECKOUT_ID}`);
    expect(api.calls.filter((c) => c.path.startsWith("/billing/checkout/"))).toHaveLength(0);
    expect(await axe(document.body)).toHaveNoViolations();
    noCardLeaks("4000 0000 0000 0002");
    await user.clear(screen.getByLabelText("Card number"));
    await user.type(screen.getByLabelText("Card number"), "4242424242424242");
    await user.click(screen.getByRole("button", { name: /^Pay / }));
    expect(await screen.findByRole("heading", { level: 1, name: copy.paywall.states.success })).toBeInTheDocument();
  }, 30000);

  it("3-D Secure card needs the Authenticate step", async () => {
    await startAtPaywall();
    await toFakeCheckout();
    await fill("4000 0025 0000 3155");
    await user.click(screen.getByRole("button", { name: /^Pay / }));
    await user.click(await screen.findByRole("button", { name: "Authenticate" }));
    expect(await screen.findByRole("heading", { level: 1, name: copy.paywall.states.success })).toBeInTheDocument();
  }, 30000);

  it("Back cancels and returns to the paywall with the canceled banner", async () => {
    await startAtPaywall();
    await toFakeCheckout();
    await user.click(screen.getByRole("button", { name: "Back" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/paywall"));
    expect(router.state.location.search).toBe("?checkout=canceled");
    expect(api.calls.some((c) => c.method === "POST" && c.path.endsWith("/cancel"))).toBe(true);
    expect(await screen.findByRole("status")).toHaveTextContent(copy.paywall.states.returnedCanceled);
  }, 30000);

  it("validates the form locally without calling the API", async () => {
    await startAtPaywall();
    await toFakeCheckout();
    await user.click(screen.getByRole("button", { name: /^Pay / }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter the card number.");
    await user.type(screen.getByLabelText("Card number"), "4242424242424242");
    await user.type(screen.getByLabelText(/Expiry/), "13");
    await user.click(screen.getByRole("button", { name: /^Pay / }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter the expiry as MM/YY");
    expect(api.calls.some((c) => c.path.endsWith("/pay"))).toBe(false);
  }, 30000);

  it("lists Stripe's test cards and 'Use' fills the form", async () => {
    await startAtPaywall();
    await toFakeCheckout();
    const list = screen.getByText("Test cards").closest("details")!;
    for (const card of TEST_CARDS) expect(within(list).getByText(card.number)).toBeInTheDocument();
    await user.click(within(list).getByRole("button", { name: "Use 4242 4242 4242 4242" }));
    expect(screen.getByLabelText("Card number")).toHaveValue("4242 4242 4242 4242");
  }, 30000);

  it("shows a not-found state for an unknown checkout id", async () => {
    api = installFakeApi({ fakeStripe: true });
    router = createMemoryRouter(routes, { initialEntries: ["/fake-checkout/cs_fake_nope"] });
    render(<RouterProvider router={router} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("couldn't find that checkout");
  });

  it("is noindex", async () => {
    await startAtPaywall();
    await toFakeCheckout();
    expect(document.querySelector('meta[name="robots"][content="noindex"]')).not.toBeNull();
  }, 30000);
});
