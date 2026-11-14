import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { AppDataProvider } from "../../../api/AppDataProvider";
import { clearToken, setToken } from "../../../api/session";
import { BANNED } from "../../../content/app/settings.test";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import "../../../test/fakeApp/demo";
import type { SubscriptionState } from "../../../test/fakeApp/registry";
import CancelPage from "./CancelPage";
import SettingsPage from "./SettingsPage";

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

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppDataProvider>
        <Routes>
          <Route element={<Outlet context={{ reportFailure: report, openHelp: () => undefined }} />}>
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/cancel" element={<CancelPage />} />
            <Route path="/settings/gentle-exit" element={<p>gentle exit page</p>} />
            <Route path="/care-card" element={<p>care card page</p>} />
          </Route>
        </Routes>
        <Where />
      </AppDataProvider>
    </MemoryRouter>,
  );
}

const statusIn = async (state: SubscriptionState) => {
  api.scenario.subscription = state;
};

describe("Settings", () => {
  it("demo: Subscription heading, plan, mode, cancel link, privacy, gentle exit, demo panel", async () => {
    const { container } = renderAt("/settings");
    await screen.findByRole("heading", { level: 1, name: "Settings" });
    await screen.findByRole("heading", { level: 2, name: "Subscription" });
    expect(await screen.findByText("4 weeks")).toBeInTheDocument();
    expect(screen.getByText("Demo mode, no payment")).toBeInTheDocument();
    expect(screen.getByText(/nothing is charged/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cancel subscription" })).toHaveAttribute("href", "/settings/cancel");
    expect(screen.getByRole("heading", { level: 2, name: "Privacy" })).toBeInTheDocument();
    expect(screen.getByText("Saved privately to this session. No account, no name needed.")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Mom has passed away or moved to a care facility" })).toHaveAttribute(
      "href",
      "/settings/gentle-exit",
    );
    expect(await screen.findByText("Demo controls: simulated time, not real time.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Fail next payment/ })).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/[{}]/);
    expect(await axe(container)).toHaveNoViolations();
  });

  it.each([
    ["active", /Your plan is active/, true],
    ["canceling", /Your plan is canceled. You keep full access until Feb 2, 2026/, false],
    ["past_due", /last payment did not go through/, true],
    ["canceled", /Your plan has ended/, false],
    ["ended", /Your plan has ended/, false],
    ["none", /do not have a plan/, false],
  ] as const)("%s renders honest text and the right cancel link", async (state, text, canCancel) => {
    await statusIn(state);
    const { container } = renderAt("/settings");
    expect(await screen.findByText(text)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Cancel subscription" }) !== null).toBe(canCancel);
    expect(container.textContent).not.toMatch(/[{}]/);
    for (const rule of BANNED) expect(container.textContent).not.toMatch(rule);
  });

  it("works in past_due: still reaches the exit and cancel", async () => {
    await statusIn("past_due");
    renderAt("/settings");
    await screen.findByRole("link", { name: "Cancel subscription" });
    expect(screen.getByRole("link", { name: /Mom has passed away/ })).toBeInTheDocument();
  });

  it("demo panel is absent when GET /demo answers 404", async () => {
    api.scenario.demoControls = false;
    renderAt("/settings");
    await screen.findByText(/nothing is charged/);
    await waitFor(() => expect(api.calls.some((c) => c.path === "/demo")).toBe(true));
    expect(screen.queryByText(/Demo controls/)).not.toBeInTheDocument();
  });

  it("fail-next-payment shows the server's 409 message on a demo session", async () => {
    renderAt("/settings");
    await userEvent.click(await screen.findByRole("button", { name: /Fail next payment/ }));
    expect(
      await screen.findByText("This control needs a card subscription made through Stripe checkout."),
    ).toBeInTheDocument();
  });

  it("simulate next day refreshes the subscription", async () => {
    renderAt("/settings");
    await userEvent.click(await screen.findByRole("button", { name: /Simulate next day/ }));
    expect(await screen.findByText("Day moved forward")).toBeInTheDocument();
    expect(api.calls.filter((c) => c.path === "/billing/subscription").length).toBeGreaterThan(1);
  });

  it("a failed subscription read shows a retry", async () => {
    const original = window.fetch;
    let first = true;
    window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      if (first && url.endsWith("/billing/subscription")) {
        first = false;
        return Promise.reject(new TypeError("Failed to fetch"));
      }
      return original(input, init);
    }) as typeof window.fetch;
    renderAt("/settings");
    await userEvent.click(await screen.findByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/nothing is charged/)).toBeInTheDocument();
  });
});

describe("Cancel", () => {
  const cancelCalls = () => api.calls.filter((c) => c.method === "POST" && c.path === "/billing/cancel");

  it("shows the facts and exactly two buttons; Keep my plan changes nothing", async () => {
    const { container } = renderAt("/settings/cancel");
    await screen.findByText(
      "If you cancel, you keep full access until Mar 2, 2026. After that you'll lose access to 4 weeks and 2 saved phrases.",
    );
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual(["Keep my plan", "Cancel anyway"]);
    for (const rule of BANNED) expect(container.textContent).not.toMatch(rule);
    expect(await axe(container)).toHaveNoViolations();
    await userEvent.click(screen.getByRole("button", { name: "Keep my plan" }));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/settings$/));
    expect(cancelCalls()).toHaveLength(0);
  });

  it("Cancel anyway calls the API once, shows the end date and hides the buttons", async () => {
    const { container } = renderAt("/settings/cancel");
    await userEvent.click(await screen.findByRole("button", { name: "Cancel anyway" }));
    const done = await screen.findByRole("status");
    expect(within(done).getByText("You keep full access until Mar 2, 2026.")).toBeInTheDocument();
    expect(cancelCalls()).toHaveLength(1);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("503 billing_cancel_failed blocks: message, no success, retry works once the provider is back", async () => {
    api.scenario.cancelFails = true;
    renderAt("/settings/cancel");
    await userEvent.click(await screen.findByRole("button", { name: "Cancel anyway" }));
    expect(
      await screen.findByText("We couldn't cancel with the payment provider, so nothing changed. Please try again."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Your plan is canceled")).not.toBeInTheDocument();
    api.scenario.cancelFails = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Your plan is canceled")).toBeInTheDocument();
  });

  it("409 shows a plain message", async () => {
    renderAt("/settings/cancel");
    await screen.findByRole("button", { name: "Cancel anyway" });
    // Another tab cancelled in the meantime.
    await fetch("/api/billing/cancel", { method: "POST", headers: { "X-Session-Token": "fake-token-app" } });
    await userEvent.click(screen.getByRole("button", { name: "Cancel anyway" }));
    expect(await screen.findByText(/can't be canceled right now/)).toBeInTheDocument();
    expect(screen.getByTestId("where")).toHaveTextContent("/settings/cancel");
  });

  it("an already canceling plan has no cancel button", async () => {
    await statusIn("canceling");
    renderAt("/settings/cancel");
    expect(await screen.findByText("Your plan is already canceled.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Settings" })).toBeInTheDocument();
  });

  it("works in past_due", async () => {
    await statusIn("past_due");
    renderAt("/settings/cancel");
    await userEvent.click(await screen.findByRole("button", { name: "Cancel anyway" }));
    expect(await screen.findByText("Your plan is canceled")).toBeInTheDocument();
  });
});
