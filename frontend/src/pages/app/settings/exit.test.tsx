import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { AppDataProvider } from "../../../api/AppDataProvider";
import { getToday } from "../../../api/app";
import { clearToken, getToken, setToken } from "../../../api/session";
import { EXIT, exitTexts } from "../../../content/app/exit";
import { BANNED } from "../../../content/app/settings.test";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import GentleExitPage from "./GentleExitPage";
import GoodbyePage from "./GoodbyePage";
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

function renderAt(path: string, state?: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: path, state }]}>
      <AppDataProvider>
        <Routes>
          <Route element={<Outlet context={{ reportFailure: report, openHelp: () => undefined }} />}>
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/gentle-exit" element={<GentleExitPage />} />
          </Route>
          <Route path="/goodbye" element={<GoodbyePage />} />
          <Route path="/" element={<p>home page</p>} />
        </Routes>
        <Where />
      </AppDataProvider>
    </MemoryRouter>,
  );
}

const buttonNames = () => screen.getAllByRole("button").map((b) => b.textContent);

describe("Gentle exit", () => {
  it("needs step 1 then step 2, with Go back at both, and offers nothing else", async () => {
    const { container } = renderAt("/settings/gentle-exit");
    await screen.findByRole("heading", { level: 2, name: EXIT.step1Heading });
    expect(buttonNames()).toEqual([EXIT.back, EXIT.continue]);
    expect(screen.getByText(/cannot be undone/)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
    await userEvent.click(screen.getByRole("button", { name: EXIT.continue }));
    await screen.findByRole("heading", { level: 2, name: EXIT.step2Heading });
    expect(buttonNames()).toEqual([EXIT.back, EXIT.confirm]);
    expect(await axe(container)).toHaveNoViolations();
    for (const rule of BANNED) expect(container.textContent).not.toMatch(rule);
    await userEvent.click(screen.getByRole("button", { name: EXIT.back }));
    expect(screen.getByTestId("where")).toHaveTextContent("/settings");
  });

  it("Go back at step 1 leaves the session untouched", async () => {
    renderAt("/settings/gentle-exit");
    await userEvent.click(await screen.findByRole("button", { name: EXIT.back }));
    expect(screen.getByTestId("where")).toHaveTextContent("/settings");
    expect(getToken()).not.toBeNull();
  });

  it("success clears the token, shows the API text and resources, and the next call is 401", async () => {
    const token = getToken();
    const { container } = renderAt("/settings/gentle-exit");
    await userEvent.click(await screen.findByRole("button", { name: EXIT.continue }));
    await userEvent.click(screen.getByRole("button", { name: EXIT.confirm }));
    await screen.findByRole("heading", { level: 1, name: "Your plan is closed" });
    expect(screen.getByTestId("where")).toHaveTextContent("/goodbye");
    expect(screen.getByText(/the time you spent caring/)).toBeInTheDocument();
    expect(screen.getByText("If it helps to talk with someone, these services are free.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "1-800-272-3900" })).toHaveAttribute("href", "tel:18002723900");
    const external = screen.getByRole("link", { name: /Hospice Foundation/ });
    expect(external).toHaveAttribute("href", "https://hospicefoundation.org/Grief-Support");
    expect(external).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("link", { name: "Back to the home page" })).toHaveAttribute("href", "/");
    expect(getToken()).toBeNull();
    expect(window.localStorage.length).toBe(0);
    expect(await axe(container)).toHaveNoViolations();
    setToken(token ?? "");
    await expect(getToday()).rejects.toMatchObject({ status: 401 });
  });

  it("503 keeps the token, says nothing was deleted and allows a retry", async () => {
    api.scenario.cancelFails = true;
    renderAt("/settings/gentle-exit");
    await userEvent.click(await screen.findByRole("button", { name: EXIT.continue }));
    await userEvent.click(screen.getByRole("button", { name: EXIT.confirm }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/nothing was deleted/);
    expect(getToken()).not.toBeNull();
    expect(screen.getByTestId("where")).toHaveTextContent("/settings/gentle-exit");
    api.scenario.cancelFails = false;
    await userEvent.click(screen.getByRole("button", { name: EXIT.retry }));
    await screen.findByRole("heading", { level: 1, name: "Your plan is closed" });
    expect(getToken()).toBeNull();
  });

  it("works from past_due", async () => {
    api.scenario.subscription = "past_due";
    renderAt("/settings/gentle-exit");
    await userEvent.click(await screen.findByRole("button", { name: EXIT.continue }));
    await userEvent.click(screen.getByRole("button", { name: EXIT.confirm }));
    await screen.findByRole("heading", { level: 1, name: "Your plan is closed" });
  });

  it("has no retention copy", () => {
    for (const text of exitTexts()) for (const rule of BANNED) expect(text).not.toMatch(rule);
  });
});

describe("Goodbye page", () => {
  it("redirects home when there is no router state (a reload)", async () => {
    renderAt("/goodbye");
    await screen.findByText("home page");
    expect(screen.getByTestId("where")).toHaveTextContent("/");
  });
});

describe("Clear my data", () => {
  it("is two steps with Go back, then shows the API message and clears the token", async () => {
    const { container } = renderAt("/settings");
    await userEvent.click(await screen.findByRole("button", { name: "Clear my data" }));
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual(
      expect.arrayContaining(["Go back", "Continue"]),
    );
    await userEvent.click(screen.getByRole("button", { name: "Go back" }));
    expect(screen.getByRole("button", { name: "Clear my data" })).toBeInTheDocument();
    expect(getToken()).not.toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Clear my data" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await axe(container)).toHaveNoViolations();
    await userEvent.click(screen.getByRole("button", { name: "Delete my data" }));
    await screen.findByText("Your data has been deleted. Your care card link no longer works.");
    expect(screen.getByTestId("where")).toHaveTextContent("/goodbye");
    expect(getToken()).toBeNull();
    expect(window.localStorage.length).toBe(0);
  });

  it("keeps the token when the call fails", async () => {
    api.scenario.subscription = "past_due";
    api.restore();
    api = installFakeApi();
    setToken(signIn(api));
    const real = globalThis.fetch;
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
      init?.method === "DELETE" ? new Response("{}", { status: 500 }) : real(input, init),
    ) as typeof fetch;
    renderAt("/settings");
    await userEvent.click(await screen.findByRole("button", { name: "Clear my data" }));
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete my data" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(getToken()).not.toBeNull();
    globalThis.fetch = real;
  });
});
