import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Outlet, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AppContext } from "../layout/app/appContext";
import { type FakeApi, installFakeApi } from "../test/fakeApi";
import { signIn } from "../test/fakeApp/core";
import { getToday } from "./app";
import { ApiError } from "./client";
import { clearToken, getToken, setToken } from "./session";
import { runAppAction, useAppAction, useAppRequest } from "./useAppRequest";

const NodeRequest = Request;
/** jsdom's AbortSignal is not accepted by Node's Request; drop it so slow runs behave like fast ones. */
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

let api: FakeApi;
const report = vi.fn<AppContext["reportFailure"]>();

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
  vi.stubGlobal("Request", TestRequest);
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  clearToken();
  report.mockReset();
  report.mockReturnValue(true);
  api = installFakeApi();
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

function Shell() {
  const context: AppContext = { openHelp: () => undefined, reportFailure: report };
  return <Outlet context={context} />;
}

function Probe() {
  const today = useAppRequest((signal) => getToday(signal), []);
  if (today.status === "loading") return <p>loading</p>;
  if (today.handled) return <p>handled by shell</p>;
  if (today.status === "error") {
    return (
      <div>
        <p>error: {today.error.kind}</p>
        <button type="button" onClick={today.retry}>
          retry
        </button>
      </div>
    );
  }
  return <p>title: {today.data.title}</p>;
}

const inShell = (): ReturnType<typeof render> =>
  render(
    <MemoryRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<Probe />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );

describe("useAppRequest", () => {
  it("loads, then shows data", async () => {
    setToken(signIn(api));
    inShell();
    expect(await screen.findByText("title: Today with Mom")).toBeInTheDocument();
    expect(report).not.toHaveBeenCalled();
  });

  it("401 clears the token and the shell is told (redirect to the quiz is the shell's job)", async () => {
    setToken("unknown-token");
    inShell();
    expect(await screen.findByText("handled by shell")).toBeInTheDocument();
    expect(report).toHaveBeenCalledWith({ kind: "session_lost" }, expect.any(String));
    expect(getToken()).toBeNull();
  });

  it.each(["no_plan", "no_subscription", "ended"] as const)("402 %s is reported to the shell", async (reason) => {
    setToken(signIn(api));
    api.scenario.accessReason = reason;
    inShell();
    expect(await screen.findByText("handled by shell")).toBeInTheDocument();
    expect(report).toHaveBeenCalledWith({ kind: "gate", reason }, expect.any(String));
  });

  it("402 past_due reaches the shell with the server's own message", async () => {
    setToken(signIn(api));
    api.scenario.subscription = "past_due";
    inShell();
    await screen.findByText("handled by shell");
    expect(report).toHaveBeenCalledWith(
      { kind: "gate", reason: "past_due" },
      "Your access needs attention. Please update your card.",
    );
  });

  it.each([
    [429, "rate_limited", "rate_limited"],
    [500, "boom", "server"],
    [423, "lesson_locked", "lesson_locked"],
  ])("%s is not a shell failure: the page shows its retry state", async (status, code, kind) => {
    setToken(signIn(api));
    api.injectError("GET", "/today", status, code, { unlockOn: "2026-01-07" });
    inShell();
    expect(await screen.findByText(`error: ${kind}`)).toBeInTheDocument();
    expect(report).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "retry" }));
    expect(await screen.findByText("title: Today with Mom")).toBeInTheDocument();
  });

  it("outside the shell nothing is handled and the page keeps the error", async () => {
    setToken("unknown-token");
    render(<MemoryRouter><Probe /></MemoryRouter>);
    expect(await screen.findByText("error: session_lost")).toBeInTheDocument();
  });

  it("network failure and timeout are plain error kinds", async () => {
    setToken(signIn(api));
    api.scenario.networkDown = true;
    inShell();
    expect(await screen.findByText("error: network")).toBeInTheDocument();
  });
});

describe("runAppAction", () => {
  it("returns data on success", async () => {
    await expect(runAppAction(() => Promise.resolve(7), report)).resolves.toEqual({ ok: true, data: 7 });
  });

  it("reports 401 and 402 to the shell and flags them handled", async () => {
    const lost = await runAppAction(() => Promise.reject(new ApiError(401, "invalid_session_token", "m")), report);
    expect(lost).toEqual({ ok: false, failure: { kind: "session_lost" }, handled: true });
    const gate = await runAppAction(
      () => Promise.reject(new ApiError(402, "payment_required", "Pay.", { reason: "past_due" })),
      report,
    );
    expect(gate).toMatchObject({ ok: false, handled: true });
    expect(report).toHaveBeenLastCalledWith({ kind: "gate", reason: "past_due" }, "Pay.");
  });

  it("returns every other failure unhandled for the caller to show", async () => {
    const res = await runAppAction(() => Promise.reject(new ApiError(503, "billing_cancel_failed", "m")), report);
    expect(res).toEqual({ ok: false, failure: { kind: "billing_failed" }, handled: false });
    expect(report).not.toHaveBeenCalled();
  });

  it("useAppAction binds the shell's reportFailure", async () => {
    setToken("unknown-token");
    let result: Awaited<ReturnType<typeof runAppAction>> | undefined;
    function Button() {
      const run = useAppAction();
      return (
        <button type="button" onClick={() => void run(() => getToday()).then((r) => (result = r))}>
          go
        </button>
      );
    }
    render(
      <MemoryRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/" element={<Button />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("button", { name: "go" }));
    await waitFor(() => expect(result).toMatchObject({ ok: false, handled: true }));
    expect(report).toHaveBeenCalledOnce();
  });
});
