import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { type FakeApi, installFakeApi } from "../test/fakeApi";
import { signIn } from "../test/fakeApp/core";
import { AppDataProvider, useAppCopy } from "./AppDataProvider";
import { clearToken, setToken } from "./session";

let api: FakeApi;
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
});
afterEach(() => api.restore());

function Show() {
  const copy = useAppCopy();
  if (copy.status === "loading") return <p>loading</p>;
  if (copy.status === "error") {
    return (
      <button type="button" onClick={copy.refresh}>
        reload {copy.error.kind}
      </button>
    );
  }
  return <p>{copy.data.nav.profilePage}</p>;
}

describe("AppDataProvider", () => {
  it("loads app-copy once for all consumers", async () => {
    setToken(signIn(api));
    render(
      <AppDataProvider>
        <Show />
        <Show />
      </AppDataProvider>,
    );
    expect(await screen.findAllByText("Mom's page")).toHaveLength(2);
    expect(api.calls.filter((c) => c.path === "/app-copy")).toHaveLength(1);
  });

  it("works without a plan or subscription (it is not behind the gate)", async () => {
    api.sessions.set("fresh", { answers: {}, lastQuestionId: null, completed: false, subscribed: false, app: {} });
    setToken("fresh");
    render(<AppDataProvider><Show /></AppDataProvider>);
    expect(await screen.findByText("Mom's page")).toBeInTheDocument();
  });

  it("exposes an error with refresh, and refresh recovers", async () => {
    setToken(signIn(api));
    api.scenario.appCopy = "error";
    render(<AppDataProvider><Show /></AppDataProvider>);
    const button = await screen.findByRole("button", { name: "reload server" });
    api.scenario.appCopy = "ok";
    await userEvent.click(button);
    expect(await screen.findByText("Mom's page")).toBeInTheDocument();
  });

  it("reloads for a new session token and never shows the old session's copy", async () => {
    setToken(signIn(api, "tok-a"));
    const { rerender } = render(<AppDataProvider><Show /></AppDataProvider>);
    await screen.findByText("Mom's page");
    clearToken();
    setToken(signIn(api, "tok-b"));
    rerender(<AppDataProvider><Show /></AppDataProvider>);
    await waitFor(() => expect(api.calls.filter((c) => c.path === "/app-copy").map((c) => c.token)).toEqual(["tok-a", "tok-b"]));
  });

  it("useAppCopy outside the provider is a wiring error", () => {
    const spy = (): void => undefined;
    const original = console.error;
    console.error = spy;
    expect(() => render(<Show />)).toThrow(/AppDataProvider/);
    console.error = original;
  });
});
