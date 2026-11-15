import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../../../api/session";
import { routes } from "../../../router";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import { appFixture } from "../../../test/fakeApp/fixtures";

const NodeRequest = Request;
class TestRequest extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal ? { ...init, signal: undefined } : init);
  }
}

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

let api: FakeApi;
beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  window.scrollTo = vi.fn();
  clearToken();
  api = installFakeApi();
  setToken(signIn(api));
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

async function openLesson(id = "m1_l1") {
  const router = createMemoryRouter(routes, { initialEntries: [`/lessons/${id}`] });
  const utils = render(<RouterProvider router={router} />);
  return { router, ...utils };
}

const progress = () => screen.getByRole("progressbar", { name: "Lesson progress" });
const next = () => screen.getByRole("button", { name: "Continue" });

async function chooseVariant(label: string) {
  const user = userEvent.setup();
  await screen.findByRole("heading", { level: 1, name: "When Mom asks again" });
  await user.click(await screen.findByRole("radio", { name: label }));
  await waitFor(() => expect(progress()).toHaveAttribute("aria-valuemax", "9"));
  return user;
}

describe("lesson player", () => {
  it("starts with the setup screen alone and re-fetches after the answer, staying on screen 1", async () => {
    await openLesson();
    await screen.findByRole("heading", { level: 1, name: "When Mom asks again" });
    expect(progress()).toHaveAttribute("aria-valuetext", "Screen 1 of 1");
    expect(next()).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Choose an option to continue.")).toBeInTheDocument();
    const user = await chooseVariant("Both");
    expect(progress()).toHaveAttribute("aria-valuetext", "Screen 1 of 9");
    expect(screen.getByRole("radio", { name: "Both" })).toBeChecked();
    await user.click(next());
    expect(progress()).toHaveAttribute("aria-valuetext", "Screen 2 of 9");
    expect(screen.getByText(/It's 6 pm/)).toBeInTheDocument();
  });

  it("the phone variant changes the scenario text, never the screen count", async () => {
    await openLesson();
    const user = await chooseVariant("On the phone");
    await user.click(next());
    expect(screen.getByText(/You're at work/)).toBeInTheDocument();
    expect(progress()).toHaveAttribute("aria-valuemax", "9");
  });

  it("shows scenario feedback with a verdict label, never 'Wrong', and lets another answer be tried", async () => {
    await openLesson();
    const user = await chooseVariant("Both");
    await user.click(next());
    await user.click(screen.getByRole("radio", { name: /Mom, I told you already/ }));
    expect(await screen.findByText("Very common")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /You're wondering about tomorrow/ }));
    expect(await screen.findByText("Good instinct")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/wrong/i);
    expect(document.body.textContent).not.toMatch(/\{/);
  });

  it("saves the picked phrase once, shows Saved, and the phrase is in GET /phrases", async () => {
    await openLesson();
    const user = await chooseVariant("Both");
    await user.click(next());
    await user.click(screen.getByRole("radio", { name: /You're wondering about tomorrow/ }));
    const save = await screen.findByRole("button", { name: "Save this phrase" });
    await user.click(save);
    expect(await screen.findByRole("button", { name: "Saved" })).toBeInTheDocument();
    expect(screen.getByText(/Saved privately to this session/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Saved" }));
    expect(api.calls.filter((c) => c.method === "POST" && c.path === "/phrases")).toHaveLength(1);
    const token = [...api.sessions.keys()][0] ?? "";
    const res = await fetch("/api/phrases", { headers: { "X-Session-Token": token } });
    const body = (await res.json()) as { phrases: { text: string; source: string; lessonId: string }[] };
    expect(body.phrases).toHaveLength(1);
    expect(body.phrases[0]).toMatchObject({
      source: "scenario",
      lessonId: "m1_l1",
      text: expect.stringContaining("You're wondering about tomorrow") as string,
    });
  });

  it("explains a full phrase book plainly", async () => {
    await openLesson();
    const user = await chooseVariant("Both");
    await user.click(next());
    await user.click(screen.getByRole("radio", { name: /You're wondering about tomorrow/ }));
    api.injectError("POST", "/phrases", 422, "phrase_limit_reached");
    await user.click(await screen.findByRole("button", { name: "Save this phrase" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/phrase book is full/i);
  });

  it("shows warm mini-task feedback and keeps answers when going Back", async () => {
    await openLesson();
    const user = await chooseVariant("Both");
    await user.click(next());
    await user.click(screen.getByRole("radio", { name: /You're wondering about tomorrow/ }));
    await screen.findByText("Good instinct");
    await user.click(next());
    await user.click(await screen.findByRole("radio", { name: "Worry" }));
    expect(await screen.findByText("Thanks for answering. Let’s keep going.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("radio", { name: /You're wondering about tomorrow/ })).toBeChecked();
    expect(screen.getByText("Good instinct")).toBeInTheDocument();
    await user.click(next());
    expect(screen.getByRole("radio", { name: "Worry" })).toBeChecked();
  });

  it("renders every screen of the lesson in order with no placeholder and no disclaimer line", async () => {
    await openLesson();
    const user = await chooseVariant("Both");
    for (let i = 1; i <= 8; i += 1) {
      expect(progress()).toHaveAttribute("aria-valuenow", String(i));
      expect(document.body.textContent).not.toMatch(/\{[a-z]/i);
      expect(screen.queryByText(/We teach and organize/)).toBeNull();
      await user.click(next());
    }
    expect(progress()).toHaveAttribute("aria-valuenow", "9");
    expect(screen.queryByRole("button", { name: "Continue" })).toBeNull();
  });

  it("is keyboard operable: Enter on Next moves on", async () => {
    await openLesson();
    const user = await chooseVariant("Both");
    next().focus();
    await user.keyboard("{Enter}");
    expect(progress()).toHaveAttribute("aria-valuenow", "2");
  });

  it("resumes at the stored step (P4) after a reload", async () => {
    const first = await openLesson();
    const user = await chooseVariant("Both");
    await user.click(next());
    await user.click(next());
    await waitFor(() =>
      expect(api.calls.filter((c) => c.method === "PUT" && c.path === "/lessons/m1_l1/progress")).toHaveLength(2),
    );
    first.unmount();
    await openLesson();
    await screen.findByRole("heading", { level: 1, name: "When Mom asks again" });
    await waitFor(() => expect(progress()).toHaveAttribute("aria-valuenow", "3"));
  });

  it("opens at screen 1 when no step is stored (documented fallback)", async () => {
    await openLesson();
    await screen.findByRole("heading", { level: 1, name: "When Mom asks again" });
    expect(progress()).toHaveAttribute("aria-valuenow", "1");
  });

  it("m1_l5 shows the phrase book screen and the recap banner", async () => {
    api.scenario.today = "all_done";
    await openLesson("m1_l5");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getByText(/Last time you practiced/)).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(next());
    expect(await screen.findByRole("heading", { name: "Your phrase book" })).toBeInTheDocument();
    expect(screen.getByText("No rush. Take my arm?")).toBeInTheDocument();
  });

  it("a locked lesson shows the formatted date and no player", async () => {
    await openLesson("m1_l2");
    expect(await screen.findByRole("heading", { level: 1, name: "This lesson isn’t open yet" })).toBeInTheDocument();
    expect(screen.getByText("It opens on Jan 7.")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.getByRole("link", { name: "Back to Today" })).toHaveAttribute("href", "/today");
  });

  it("an unknown lesson id says so calmly", async () => {
    await openLesson("nope");
    expect(await screen.findByRole("heading", { level: 1, name: "We can’t find this lesson" })).toBeInTheDocument();
  });

  it("a server error shows a retry that works", async () => {
    api.injectError("GET", "/lessons/m1_l1", 500, "internal_error");
    await openLesson();
    const retry = await screen.findByRole("button", { name: "Try again" });
    await userEvent.setup().click(retry);
    expect(await screen.findByRole("heading", { level: 1, name: "When Mom asks again" })).toBeInTheDocument();
  });

  it("an unknown screen type shows the calm message and Next still works", async () => {
    const lesson = appFixture<{ screens: Record<string, unknown>[] }>("lesson-m1_l1-both");
    lesson.screens[1] = { id: "s2_future", type: "hologram", surprise: true };
    api.inject({ method: "GET", path: "/lessons/m1_l1", status: 200, body: lesson, times: 1 });
    await openLesson();
    await screen.findByRole("heading", { level: 1, name: "When Mom asks again" });
    const user = userEvent.setup();
    await user.click(next());
    expect(await screen.findByText("This part can’t be shown in this version")).toBeInTheDocument();
    await user.click(next());
    expect(progress()).toHaveAttribute("aria-valuenow", "3");
  });

  it("never logs or stores anything", async () => {
    const spy = vi.spyOn(console, "log");
    await openLesson();
    const user = await chooseVariant("Both");
    await user.click(next());
    expect(spy).not.toHaveBeenCalled();
    expect(Object.keys(window.localStorage)).not.toContain("lesson");
  });

  it("has no axe violations on setup, scenario and learn screens", async () => {
    const { container } = await openLesson();
    const user = await chooseVariant("Both");
    expect(await axe(container)).toHaveNoViolations();
    await user.click(next());
    expect(await axe(container)).toHaveNoViolations();
    await user.click(screen.getByRole("radio", { name: /You're wondering about tomorrow/ }));
    await screen.findByText("Good instinct");
    expect(await axe(container)).toHaveNoViolations();
    await user.click(next());
    expect(await axe(container)).toHaveNoViolations();
    expect(within(container).getAllByRole("main")).toHaveLength(1);
  });
});
