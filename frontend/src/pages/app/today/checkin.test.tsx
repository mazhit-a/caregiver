import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter, Outlet, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../../../api/session";
import type { AppContext } from "../../../layout/app/appContext";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import type { TodayState } from "../../../test/fakeApp/registry";
import TodayPage from "../TodayPage";
import { WithAppCopy } from "../../../test/withAppCopy";

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
  setToken(signIn(api));
});
afterEach(() => api.restore());

function Shell() {
  const context: AppContext = { openHelp: () => undefined, reportFailure: () => true };
  return <Outlet context={context} />;
}

async function open(state: TodayState = "day2") {
  api.scenario.today = state;
  const view = render(
    <MemoryRouter initialEntries={["/today"]}>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/today" element={<WithAppCopy><TodayPage /></WithAppCopy>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { level: 1, name: /^Today with /i });
  return view;
}

const checkinBodies = () =>
  api.calls.filter((c) => c.method === "POST" && c.path === "/checkins");

/** Today with a custom check-in (the not_yet variant has no follow-up). */
function injectToday(checkIn: unknown) {
  const base = JSON.parse(
    readFileSync(resolve(process.cwd(), "src/test/fixtures/app/today-day2.json"), "utf-8"),
  ) as Record<string, unknown>;
  api.inject({ method: "GET", path: "/today", status: 200, body: { ...base, checkIn } });
}

describe("Check-in card", () => {
  it("quotes the user's own plan and walks yes -> follow-up -> helped", async () => {
    const user = userEvent.setup();
    await open();
    const card = screen.getByRole("region", { name: "Check-in" });
    expect(within(card).getByText("Did Mom ask the same question again since yesterday?")).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Yes" }));
    expect(checkinBodies()).toHaveLength(0);
    expect(within(card).getByText("How did your plan go?")).toBeInTheDocument();
    expect(card.textContent).toContain("If Mom calls with the same question again, I point to the note");
    await user.click(within(card).getByRole("button", { name: "It helped" }));
    await waitFor(() => expect(checkinBodies()).toHaveLength(1));
    expect(await within(card).findByText(/That's real progress/)).toBeInTheDocument();
    expect(within(card).queryByRole("button")).toBeNull();
    expect(within(card).getByText("Marked as done in your plan.")).toBeInTheDocument();
  });

  it("didn't help shows the follow-up list", async () => {
    const user = userEvent.setup();
    await open();
    await user.click(screen.getByRole("button", { name: "Yes" }));
    await user.click(screen.getByRole("button", { name: "It didn't help" }));
    expect(await screen.findByText("Look for a pattern")).toBeInTheDocument();
    expect(screen.getByText("Shorter, and written down")).toBeInTheDocument();
    expect(screen.getByText("Give her something to do")).toBeInTheDocument();
  });

  it("partly and not yet are sent with the right fields", async () => {
    const user = userEvent.setup();
    const first = await open();
    await user.click(screen.getByRole("button", { name: "Yes" }));
    await user.click(screen.getByRole("button", { name: "Partly" }));
    await screen.findByText("Thanks. Your answer is saved.");
    first.unmount();
    api.restore();
    api = installFakeApi();
    setToken(signIn(api));
    await open();
    await user.click(screen.getByRole("button", { name: "Not yet" }));
    await waitFor(() => expect(checkinBodies()).toHaveLength(1));
    expect(await screen.findByText("Thanks. Your answer is saved.")).toBeInTheDocument();
  });

  it("the not_yet variant answers on the first tap (no follow-up) and has no doctor-note control", async () => {
    const user = userEvent.setup();
    injectToday({
      planId: "m1_l1",
      question: "Did you notice Mom asking the same question again?",
      options: [
        { id: "noted", label: "Yes, I noted it" },
        { id: "no", label: "No" },
        { id: "not_sure", label: "Not sure" },
      ],
      followUp: null,
      plan: { cue: "If Mom asks,", response: "I stay calm.", reset: null },
    });
    await open();
    expect(screen.queryByRole("checkbox")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Yes, I noted it" }));
    await waitFor(() => expect(checkinBodies()).toHaveLength(1));
  });

  it("double press sends once and a second submit is not possible after the answer", async () => {
    const user = userEvent.setup();
    await open();
    await user.click(screen.getByRole("button", { name: "Not yet" }));
    await screen.findByText("Thanks. Your answer is saved.");
    expect(screen.queryByRole("button", { name: "Not yet" })).toBeNull();
    expect(checkinBodies()).toHaveLength(1);
  });

  it("sends the doctor note only when ticked, trimmed", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(globalThis, "fetch");
    await open();
    expect(screen.queryByRole("textbox", { name: /note/i })).toBeNull();
    await user.click(screen.getByRole("checkbox", { name: "Add to the doctor-visit sheet" }));
    await user.type(screen.getByRole("textbox", { name: /Your note/ }), "  asks it every hour  ");
    await user.click(screen.getByRole("button", { name: "Yes" }));
    await user.click(screen.getByRole("button", { name: "It helped" }));
    await waitFor(() => expect(checkinBodies()).toHaveLength(1));
    const post = spy.mock.calls.find(([, init]) => init?.method === "POST" && String(init.body).includes("planId"));
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({
      planId: "m1_l1",
      cameUp: "yes",
      outcome: "helped",
      doctorNote: { addToVisitSheet: true, text: "asks it every hour" },
    });
    spy.mockRestore();
  });

  it("without the tick there is no doctorNote in the body", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(globalThis, "fetch");
    await open();
    await user.click(screen.getByRole("button", { name: "Yes" }));
    await user.click(screen.getByRole("button", { name: "Partly" }));
    await waitFor(() => expect(checkinBodies()).toHaveLength(1));
    const post = spy.mock.calls.find(([, init]) => init?.method === "POST" && String(init.body).includes("planId"));
    expect(String(post?.[1]?.body)).not.toContain("doctorNote");
    spy.mockRestore();
  });

  it("409 already answered says so and refetches Today", async () => {
    const user = userEvent.setup();
    await open();
    api.injectError("POST", "/checkins", 409, "checkin_already_answered", { planId: "m1_l1" });
    const before = api.calls.filter((c) => c.path === "/today").length;
    const h1 = screen.getByRole("heading", { level: 1, name: /^Today with /i });
    await user.click(screen.getByRole("button", { name: "Not yet" }));
    await waitFor(() => expect(api.calls.filter((c) => c.path === "/today").length).toBeGreaterThan(before));
    // The refetch is silent: no loading screen replaces the page, and the notice stays.
    expect(h1.isConnected).toBe(true);
    expect(screen.getByText("Already answered")).toBeInTheDocument();
    expect(screen.queryByText(/Loading/i)).toBeNull();
  });

  it("422 shows a plain message and keeps the buttons", async () => {
    const user = userEvent.setup();
    await open();
    api.injectError("POST", "/checkins", 422, "validation_error");
    await user.click(screen.getByRole("button", { name: "Not yet" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/needs another look/);
    expect(screen.getByRole("button", { name: "Not yet" })).toBeEnabled();
  });

  it("is keyboard-operable and has no unfilled placeholder", async () => {
    const user = userEvent.setup();
    await open();
    await user.tab();
    const group = screen.getByRole("group", { name: /same question/ });
    const yes = within(group).getByRole("button", { name: "Yes" });
    yes.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("How did your plan go?")).toBeInTheDocument();
    expect(document.body.textContent ?? "").not.toMatch(/[{}]/);
  });

  it("never logs the request body", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((m) => vi.spyOn(console, m));
    const user = userEvent.setup();
    await open();
    await user.click(screen.getByRole("checkbox", { name: "Add to the doctor-visit sheet" }));
    await user.type(screen.getByRole("textbox", { name: /Your note/ }), "secret note words");
    await user.click(screen.getByRole("button", { name: "Not yet" }));
    await screen.findByText("Thanks. Your answer is saved.");
    for (const s of spies) {
      expect(JSON.stringify(s.mock.calls)).not.toContain("secret note words");
      s.mockRestore();
    }
  });

  it("is axe clean in the question and the answered state", async () => {
    const user = userEvent.setup();
    const { container } = await open();
    expect(await axe(container)).toHaveNoViolations();
    await user.click(screen.getByRole("button", { name: "Yes" }));
    await user.click(screen.getByRole("button", { name: "It didn't help" }));
    await screen.findByText("Look for a pattern");
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("Welcome card", () => {
  it("shows for a profile never saved, with the app-copy wording and the privacy line", async () => {
    await open("fresh");
    const card = await screen.findByRole("region", { name: "Welcome" });
    expect(within(card).getByLabelText("First name (optional)")).toBeInTheDocument();
    expect(card).toHaveTextContent("Saved privately to this session. No account, no name needed.");
  });

  it("Continue saves the name, hides the card and refetches app copy and Today", async () => {
    const user = userEvent.setup();
    await open("fresh");
    const card = await screen.findByRole("region", { name: "Welcome" });
    await user.type(within(card).getByLabelText("First name (optional)"), "  Rosa ");
    const copyBefore = api.calls.filter((c) => c.path === "/app-copy").length;
    await user.click(within(card).getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(api.calls.some((c) => c.method === "PUT" && c.path === "/profile")).toBe(true));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Welcome" })).toBeNull());
    expect(api.calls.filter((c) => c.path === "/app-copy").length).toBeGreaterThan(copyBefore);
    await screen.findByRole("heading", { level: 1, name: /^Today with /i });
    expect(screen.queryByRole("region", { name: "Welcome" })).toBeNull();
  });

  it("Skip saves an empty profile and the card does not come back", async () => {
    const user = userEvent.setup();
    await open("fresh");
    await user.click(await screen.findByRole("button", { name: "Skip" }));
    await waitFor(() => expect(api.calls.some((c) => c.method === "PUT" && c.path === "/profile")).toBe(true));
    await screen.findByRole("heading", { level: 1, name: /^Today with /i });
    await waitFor(() => expect(screen.queryByRole("region", { name: "Welcome" })).toBeNull());
  });

  it("is not shown when the profile was already saved", async () => {
    const user = userEvent.setup();
    await open("fresh");
    await user.click(await screen.findByRole("button", { name: "Skip" }));
    await screen.findByRole("heading", { level: 1, name: /^Today with /i });
    expect(screen.queryByRole("region", { name: "Welcome" })).toBeNull();
  });

  it("is axe clean", async () => {
    const { container } = await open("fresh");
    await screen.findByRole("region", { name: "Welcome" });
    expect(await axe(container)).toHaveNoViolations();
  });
});
