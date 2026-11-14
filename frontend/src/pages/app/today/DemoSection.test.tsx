import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { getToday } from "../../../api/app";
import type { Today } from "../../../api/appTypes";
import { clearToken, setToken } from "../../../api/session";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import "../../../test/fakeApp/demo";
import type { TodayState } from "../../../test/fakeApp/registry";
import { DemoSection } from "./DemoSection";

let api: FakeApi;
let token: string;

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
  token = signIn(api);
  setToken(token);
});
afterEach(() => {
  vi.useRealTimers();
  api.restore();
});

const session = () => api.sessions.get(token)?.app ?? {};
const posts = () => api.calls.filter((c) => c.method === "POST" && c.path.startsWith("/demo/"));

/** Fetches Today like the page does, keeps showing the old data while refetching. */
function Harness() {
  const [today, setToday] = useState<Today | null>(null);
  const [version, setVersion] = useState(0);
  const load = () => void getToday().then(setToday);
  if (today === null && version === 0) {
    setVersion(1);
    load();
  }
  if (!today) return <p>loading</p>;
  return (
    <main>
      <DemoSection today={today} onChanged={load} />
      <p data-testid="step">{today.nextStep.kind === "lesson" ? "lesson" : "rest"}</p>
      <p data-testid="checkin">{today.order.includes("checkIn") ? "checkin" : "none"}</p>
    </main>
  );
}

async function setup(state: TodayState = "after_lesson_1") {
  api.scenario.today = state;
  render(
    <MemoryRouter>
      <Harness />
    </MemoryRouter>,
  );
  await screen.findByText("Demo controls: simulated time, not real time.");
}

describe("DemoSection", () => {
  it("is absent when Today has no demo block", async () => {
    api.scenario.demoControls = false;
    render(
      <MemoryRouter>
        <Harness />
      </MemoryRouter>,
    );
    await screen.findByTestId("step");
    expect(screen.queryByText(/Demo controls/)).toBeNull();
    expect(screen.queryByRole("button", { name: /demo/i })).toBeNull();
  });

  it("shows the server label and the labelled controls, axe clean", async () => {
    await setup();
    expect(screen.getByRole("button", { name: "Simulate next day (demo)" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Jump to renewal (demo)" })).toBeEnabled();
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("does not render an unknown control id", async () => {
    api.scenario.today = "fresh";
    render(
      <MemoryRouter>
        <DemoSection
          today={
            {
              demo: {
                label: "L",
                appNow: "",
                appToday: "2026-01-05",
                clockOffsetSeconds: 0,
                controls: [
                  { id: "nextDay", label: "Simulate next day (demo)" },
                  { id: "bogus", label: "Bogus" },
                ],
              },
            } as unknown as Today
          }
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("button", { name: "Simulate next day (demo)" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Bogus" })).toBeNull();
  });

  it("next day: one call, announces it, refetches Today and the check-in appears", async () => {
    const user = userEvent.setup();
    await setup();
    expect(screen.getByTestId("checkin")).toHaveTextContent("none");
    await user.click(screen.getByRole("button", { name: "Simulate next day (demo)" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Day moved forward");
    await waitFor(() => expect(screen.getByTestId("checkin")).toHaveTextContent("checkin"));
    expect(posts().filter((c) => c.path === "/demo/next-day")).toHaveLength(1);
    expect(screen.getByText(/Simulated date: Jan 13, 2026/)).toBeInTheDocument();
  });

  it("jump to renewal calls its own endpoint", async () => {
    const user = userEvent.setup();
    await setup();
    await user.click(screen.getByRole("button", { name: "Jump to renewal (demo)" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Jumped to the renewal date");
    expect(posts().map((c) => c.path)).toEqual(["/demo/jump-to-renewal"]);
  });

  it("a second press while one is running is ignored", async () => {
    await setup();
    const button = screen.getByRole("button", { name: "Simulate next day (demo)" });
    await act(async () => {
      button.click();
      button.click();
    });
    await screen.findByText("Day moved forward");
    expect(posts()).toHaveLength(1);
  });

  it("a failure shows an inline error with retry and changes nothing", async () => {
    const user = userEvent.setup();
    await setup();
    session()["demoFail"] = true;
    await user.click(screen.getByRole("button", { name: "Simulate next day (demo)" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/went wrong/i);
    expect(screen.getByTestId("checkin")).toHaveTextContent("none");
    expect(screen.queryByText(/Simulated date: Jan 13/)).toBeNull();
    session()["demoFail"] = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Day moved forward")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(posts()).toHaveLength(2);
  });

  describe("Stripe clock sync", () => {
    it("polls every 2 s until done, then stops", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      await setup();
      session()["demoSyncPolls"] = 2;
      const subs = () => api.calls.filter((c) => c.path === "/billing/subscription").length;
      await act(async () => {
        screen.getByRole("button", { name: "Simulate next day (demo)" }).click();
      });
      await screen.findByText("Syncing with the Stripe test clock");
      expect(subs()).toBe(0);
      await act(() => vi.advanceTimersByTimeAsync(2000));
      await act(() => vi.advanceTimersByTimeAsync(2000));
      await act(() => vi.advanceTimersByTimeAsync(2000));
      expect(await screen.findByText("Stripe test clock is in sync")).toBeInTheDocument();
      expect(subs()).toBe(3);
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(subs()).toBe(3);
    });

    it("stops after 15 polls when the sync never ends", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      await setup();
      session()["demoSyncPolls"] = Infinity;
      const subs = () => api.calls.filter((c) => c.path === "/billing/subscription").length;
      await act(async () => {
        screen.getByRole("button", { name: "Simulate next day (demo)" }).click();
      });
      await screen.findByText("Syncing with the Stripe test clock");
      for (let i = 0; i < 20; i += 1) await act(() => vi.advanceTimersByTimeAsync(2000));
      expect(subs()).toBe(15);
      expect(screen.getByText(/Still syncing/)).toBeInTheDocument();
    });

    it("is cancelled when the section unmounts", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      const view = render(
        <MemoryRouter>
          <Harness />
        </MemoryRouter>,
      );
      await screen.findByText("Demo controls: simulated time, not real time.");
      session()["demoSyncPolls"] = Infinity;
      await act(async () => {
        screen.getByRole("button", { name: "Simulate next day (demo)" }).click();
      });
      await screen.findByText("Syncing with the Stripe test clock");
      view.unmount();
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(api.calls.filter((c) => c.path === "/billing/subscription")).toHaveLength(0);
    });
  });
});
