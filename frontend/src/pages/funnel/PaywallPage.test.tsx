import { readFileSync } from "node:fs";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { createSession } from "../../api/funnel";
import { clearToken, getToken } from "../../api/session";
import { routes } from "../../router";
import { type FakeApi, FAKE_CHECKOUT_URL, installFakeApi } from "../../test/fakeApi";
import copy from "../../test/fixtures/funnel-copy.json";

vi.mock("./checkoutRedirect", async (importActual) => ({
  ...(await importActual<typeof import("./checkoutRedirect")>()),
  isStripeCheckoutUrl: (url: string) => url.startsWith("https://checkout.stripe.com/"),
  goToCheckout: vi.fn(),
}));
import { goToCheckout } from "./checkoutRedirect";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

let api: FakeApi;
beforeEach(async () => {
  vi.stubGlobal("Request", TestRequest);
  window.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
  vi.mocked(goToCheckout).mockReset();
  clearToken();
});
afterEach(() => api?.restore());

async function setup(entry = "/paywall", opts: Parameters<typeof installFakeApi>[0] = {}) {
  api = installFakeApi(opts);
  await createSession();
  const state = api.sessions.get(getToken() ?? "");
  if (state) state.completed = true;
  const router = createMemoryRouter(routes, { initialEntries: [entry] });
  const utils = render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { level: 1, name: copy.paywall.headline });
  return { router, ...utils };
}

const [four, twelve] = copy.paywall.plans as [
  (typeof copy.paywall.plans)[number],
  (typeof copy.paywall.plans)[number],
];
const pay = (p: { payButtonLabel: string }) => screen.getByRole("button", { name: p.payButtonLabel });
const demo = () => screen.getByRole("button", { name: /Continue in demo mode/ });

describe("PaywallPage", () => {
  it("preselects the default plan and updates terms and Pay label on switch", async () => {
    await setup();
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(copy.paywall.plans.length);
    expect(screen.getByRole("radio", { name: new RegExp(four.label) })).toBeChecked();
    expect(screen.getByText(four.consentLabel)).toBeTruthy();
    for (const item of copy.paywall.includes) expect(screen.getByText(item)).toBeTruthy();
    await userEvent.click(screen.getByRole("radio", { name: new RegExp(twelve.label) }));
    expect(pay(twelve)).toBeTruthy();
    expect(screen.getByText(twelve.consentLabel)).toBeTruthy();
    expect(screen.getByText(twelve.disclosure[0]?.text ?? "")).toBeTruthy();
  });

  it("has no consent checkbox: the descriptor line sits with the buttons and the buttons are enabled", async () => {
    await setup();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.getByText(four.consentLabel)).toBeTruthy();
    expect(pay(four)).not.toHaveAttribute("aria-disabled", "true");
    expect(demo()).not.toHaveAttribute("aria-disabled", "true");
  });

  it("starts demo mode, sending consent as true, with the plan, then opens Today", async () => {
    const { router } = await setup();
    await userEvent.click(demo());
    await waitFor(() => expect(router.state.location.pathname).toBe("/today"));
    expect(api.calls.filter((c) => c.path === "/billing/demo")).toHaveLength(1);
  });

  it("assigns only a checkout.stripe.com URL and sends one request on double click", async () => {
    await setup("/paywall", { stripeConfigured: true });
    const button = pay(four);
    await userEvent.dblClick(button);
    await waitFor(() => expect(goToCheckout).toHaveBeenCalledWith(FAKE_CHECKOUT_URL));
    expect(api.calls.filter((c) => c.path === "/billing/checkout")).toHaveLength(1);
  });

  it("refuses a non-Stripe checkout host", async () => {
    await setup("/paywall", { stripeConfigured: true });
    api.inject({
      method: "POST",
      path: "/billing/checkout",
      status: 200,
      body: { checkoutId: "x", url: "https://evil.example.com/pay" },
    });
    await userEvent.click(pay(four));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(goToCheckout).not.toHaveBeenCalled();
  });

  it("follows the same-origin /fake-checkout path in-app, without leaving the page", async () => {
    const { router } = await setup("/paywall", { fakeStripe: true });
    await userEvent.click(pay(four));
    await waitFor(() => expect(router.state.location.pathname).toMatch(/^\/fake-checkout\/cs_fake_/));
    expect(goToCheckout).not.toHaveBeenCalled();
  });

  it("refuses a fake-checkout path on another host", async () => {
    await setup("/paywall", { stripeConfigured: true });
    api.inject({
      method: "POST",
      path: "/billing/checkout",
      status: 200,
      body: { checkoutId: "x", url: "https://evil.example.com/fake-checkout/x" },
    });
    await userEvent.click(pay(four));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(goToCheckout).not.toHaveBeenCalled();
  });

  it("shows the demo hint and focuses the demo button on 502 demo_mode", async () => {
    await setup();
    await userEvent.click(pay(four));
    expect(await screen.findByText(/For reviewers/)).toBeTruthy();
    expect(demo()).toHaveFocus();
  });

  it("shows the canceled banner", async () => {
    await setup("/paywall?checkout=canceled");
    expect(screen.getByRole("status")).toHaveTextContent(copy.paywall.states.returnedCanceled);
  });

  it("goes to Today when already subscribed (409 on start)", async () => {
    const { router } = await setup();
    api.injectError("POST", "/billing/demo", 409, "already_subscribed");
    await userEvent.click(demo());
    await waitFor(() => expect(router.state.location.pathname).toBe("/today"));
  });

  it("goes to Today at entry when the probe says subscribed", async () => {
    api = installFakeApi();
    await createSession();
    const state = api.sessions.get(getToken() ?? "");
    if (state) Object.assign(state, { completed: true, subscribed: true });
    const router = createMemoryRouter(routes, { initialEntries: ["/paywall"] });
    render(<RouterProvider router={router} />);
    await waitFor(() => expect(router.state.location.pathname).toBe("/today"));
  });

  it("keeps state and shows a message when the request fails", async () => {
    await setup();
    api.injectError("POST", "/billing/demo", 500, "server_error");
    await userEvent.click(demo());
    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("has no pressure or per-day wording, and is axe clean", async () => {
    const { container } = await setup();
    expect(container.textContent).not.toMatch(
      /per day|\/day|% off|limited time|most popular|hurry/i,
    );
    expect(container.textContent).not.toContain("{");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("formats nothing in the browser", () => {
    for (const file of ["PaywallPage.tsx", "PlanPicker.tsx"]) {
      const source = readFileSync(`${process.cwd()}/src/pages/funnel/${file}`, "utf8");
      expect(source).not.toMatch(/Intl\.NumberFormat|toFixed|new Date/);
    }
  });
});
