import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { answerLesson, putLessonProgress } from "../../../api/app";
import { clearToken, setToken } from "../../../api/session";
import { routes } from "../../../router";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";

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
  api = installFakeApi({ lesson24: true });
  setToken(signIn(api));
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

const progress = () => screen.getByRole("progressbar", { name: "Lesson progress" });
/** The player's footer button; its label is "Start the lesson" on the intro and "Continue" elsewhere. */
const footer = (name: string | RegExp = "Continue") => screen.getByRole("button", { name });

function openLesson() {
  const router = createMemoryRouter(routes, { initialEntries: ["/lessons/m1_l1"] });
  return render(<RouterProvider router={router} />);
}

/** The server side of a reload: a chosen variant and a stored step. */
async function storedAt(step: number) {
  await answerLesson("m1_l1", { screenId: "setup", value: "in_person" });
  await putLessonProgress("m1_l1", step);
}

describe("lesson 1 player (24 screens)", () => {
  it("opens on the intro with the full count and a Start the lesson button", async () => {
    openLesson();
    await screen.findByRole("heading", { level: 2, name: "When Mom asks again" });
    expect(progress()).toHaveAttribute("aria-valuemax", "24");
    expect(progress()).toHaveAttribute("aria-valuetext", "Screen 1 of 24");
    expect(screen.getByText("1 of 24")).toBeInTheDocument();
    expect(footer("Start the lesson")).not.toHaveAttribute("aria-disabled", "true");
    expect(screen.queryByRole("button", { name: "Continue" })).toBeNull();
  });

  it("locks Continue on the setup screen until a variant is chosen, with a hint", async () => {
    openLesson();
    const user = userEvent.setup();
    await screen.findByRole("heading", { level: 2, name: "When Mom asks again" });
    await user.click(footer("Start the lesson"));
    await screen.findByRole("heading", { level: 2, name: /repeated questions usually reach you/ });
    expect(progress()).toHaveAttribute("aria-valuemax", "24");
    const button = footer();
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Choose an option to continue.")).toBeInTheDocument();
    await user.click(button);
    expect(progress()).toHaveAttribute("aria-valuenow", "2");
    await user.click(await screen.findByRole("radio", { name: "In person" }));
    await waitFor(() => expect(footer()).not.toHaveAttribute("aria-disabled", "true"));
    expect(screen.queryByText("Choose an option to continue.")).toBeNull();
    await user.click(footer());
    expect(progress()).toHaveAttribute("aria-valuenow", "3");
    expect(progress()).toHaveAttribute("aria-valuemax", "24");
  });

  it("locks a quiz until it is answered, unlocks after, and Back keeps the answer", async () => {
    await storedAt(5);
    openLesson();
    const user = userEvent.setup();
    await screen.findByRole("heading", { level: 2, name: /Mom asks again five minutes after/ });
    expect(progress()).toHaveAttribute("aria-valuenow", "6");
    expect(footer()).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Choose an answer to continue.")).toBeInTheDocument();
    await user.click(footer());
    expect(progress()).toHaveAttribute("aria-valuenow", "6");
    const first = screen.getAllByRole("radio")[0] as HTMLElement;
    await user.click(first);
    await screen.findByRole("status");
    await waitFor(() => expect(footer()).not.toHaveAttribute("aria-disabled", "true"));
    await user.click(footer());
    expect(progress()).toHaveAttribute("aria-valuenow", "7");
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getAllByRole("radio")[0]).toBeChecked();
    expect(footer()).not.toHaveAttribute("aria-disabled", "true");
  });

  it("resumes at the stored step: passed screens stay open, the current one must be answered again", async () => {
    await storedAt(10);
    openLesson();
    const user = userEvent.setup();
    await waitFor(() => expect(progress()).toHaveAttribute("aria-valuenow", "11"));
    expect(progress()).toHaveAttribute("aria-valuemax", "24");
    expect(footer()).toHaveAttribute("aria-disabled", "true");
    await user.click(screen.getByRole("button", { name: "Back" }));
    await user.click(screen.getByRole("button", { name: "Back" }));
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(progress()).toHaveAttribute("aria-valuenow", "8");
    expect(footer()).not.toHaveAttribute("aria-disabled", "true");
    await user.click(footer());
    await user.click(footer());
    await user.click(footer());
    expect(progress()).toHaveAttribute("aria-valuenow", "11");
    expect(footer()).toHaveAttribute("aria-disabled", "true");
  });

  it("resumes on a teaching screen at step 12 and never locks it", async () => {
    await storedAt(12);
    openLesson();
    await waitFor(() => expect(progress()).toHaveAttribute("aria-valuenow", "13"));
    expect(footer()).not.toHaveAttribute("aria-disabled", "true");
  });

  it("moves focus to the screen heading on each step, with the part label above it", async () => {
    await storedAt(2);
    openLesson();
    const user = userEvent.setup();
    await waitFor(() => expect(progress()).toHaveAttribute("aria-valuenow", "3"));
    await user.click(screen.getAllByRole("radio")[1] as HTMLElement);
    await waitFor(() => expect(footer()).not.toHaveAttribute("aria-disabled", "true"));
    await user.click(footer());
    const heading = await screen.findByRole("heading", { level: 2, name: "New information doesn’t stick" });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(heading.previousElementSibling ?? heading.parentElement?.previousElementSibling).not.toBeNull();
  });

  it("shows what was learned on the wrap screen", async () => {
    await storedAt(23);
    openLesson();
    await waitFor(() => expect(progress()).toHaveAttribute("aria-valuenow", "24"));
    expect(await screen.findByRole("heading", { level: 2, name: "New skill: handling repeated questions" })).toBeInTheDocument();
    expect(screen.getByText("The answer fades, but the feeling stays.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Continue" })).toBeNull();
  });

  it("has no axe violations on a gated screen", async () => {
    await storedAt(5);
    const { container } = openLesson();
    await screen.findByText("Choose an answer to continue.");
    expect(await axe(container)).toHaveNoViolations();
  });
});
