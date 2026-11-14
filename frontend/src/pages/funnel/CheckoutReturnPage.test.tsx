import { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { createSession } from "../../api/funnel";
import { clearToken } from "../../api/session";
import { routes } from "../../router";
import { type FakeApi, installFakeApi } from "../../test/fakeApi";
import copy from "../../test/fixtures/funnel-copy.json";

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
  clearToken();
});
afterEach(() => api?.restore());

async function setup(
  entry = "/checkout/return?checkout_id=cs_test_fake",
  opts: Parameters<typeof installFakeApi>[0] = { stripeConfigured: true },
  withSession = true,
  networkDown = false,
) {
  api = installFakeApi(opts);
  if (withSession) await createSession();
  if (networkDown) api.scenario.networkDown = true;
  const router = createMemoryRouter(routes, { initialEntries: [entry] });
  const utils = render(
    <StrictMode>
      <RouterProvider router={router} />
    </StrictMode>,
  );
  return { router, ...utils };
}

const statusCalls = () => api.calls.filter((c) => c.path.startsWith("/billing/checkout/"));

describe("CheckoutReturnPage", () => {
  it("reconciles once (StrictMode), shows success and waits for Continue", async () => {
    const { router, container } = await setup();
    expect(await screen.findByRole("heading", { level: 1, name: copy.paywall.states.success })).toBeTruthy();
    expect(statusCalls()).toHaveLength(1);
    expect(router.state.location.pathname).toBe("/checkout/return");
    expect(window.location.search).not.toContain("checkout_id");
    expect(await axe(container)).toHaveNoViolations();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/today"));
  });

  it("explains an unpaid checkout and Check again re-asks", async () => {
    await setup(undefined, { stripeConfigured: true, checkoutPaid: false });
    expect(await screen.findByRole("heading", { name: /haven't received the payment/ })).toBeTruthy();
    expect(statusCalls()).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Back to your plan" })).toBeTruthy();
    api.scenario.checkoutPaid = true;
    await userEvent.click(screen.getByRole("button", { name: "Check again" }));
    expect(await screen.findByRole("heading", { name: copy.paywall.states.success })).toBeTruthy();
    expect(statusCalls()).toHaveLength(2);
  });

  it("redirects to the paywall without an id and to the quiz without a token", async () => {
    const a = await setup("/checkout/return");
    await waitFor(() => expect(a.router.state.location.pathname).toBe("/paywall"));
    expect(statusCalls()).toHaveLength(0);
  });

  it("redirects to the quiz without a session token", async () => {
    const b = await setup(undefined, { stripeConfigured: true }, false);
    await waitFor(() => expect(b.router.state.location.pathname).toBe("/quiz"));
  });

  it("shows an honest message for an unknown checkout", async () => {
    api = installFakeApi({ stripeConfigured: true });
    await createSession();
    api.injectError("GET", "/billing/checkout/cs_test_fake", 404, "checkout_not_found");
    render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/checkout/return?checkout_id=cs_test_fake"] })} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't find that checkout/);
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("shows the demo hint for a 502 gateway-not-configured answer", async () => {
    await setup(undefined, { stripeConfigured: false });
    expect(await screen.findByRole("alert")).toHaveTextContent(/Online payments aren't switched on/);
    expect(screen.getByText(/For reviewers/)).toBeTruthy();
  });

  it("handles a network error with retry and never navigates by itself", async () => {
    const { router } = await setup(undefined, { stripeConfigured: true }, true, true);
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't reach the server/);
    api.scenario.networkDown = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: copy.paywall.states.success })).toBeTruthy();
    expect(router.state.location.pathname).toBe("/checkout/return");
  });
});
