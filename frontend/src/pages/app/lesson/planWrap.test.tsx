import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
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

interface Sent {
  method: string;
  path: string;
  body: Record<string, unknown>;
}
let api: FakeApi;
let sent: Sent[];
let token: string;
let download: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  window.scrollTo = vi.fn();
  clearToken();
  api = installFakeApi();
  token = signIn(api);
  setToken(token);
  const base = globalThis.fetch;
  sent = [];
  vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) => {
    sent.push({
      method: (init?.method ?? "GET").toUpperCase(),
      path: String(input).replace(/^\/api/, ""),
      body: typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : {},
    });
    return base(input, init);
  });
  download = vi.fn(() => "blob:ics");
  Object.assign(URL, { createObjectURL: download, revokeObjectURL: vi.fn() });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const answers = () =>
  sent.filter((c) => c.method === "POST" && c.path === "/lessons/m1_l1/answers" && c.body["screenId"] !== "s1_setup");
const next = () => screen.getByRole("button", { name: "Next" });

async function goTo(heading: string, lesson = "m1_l1") {
  const router = createMemoryRouter(routes, { initialEntries: [`/lessons/${lesson}`] });
  const utils = render(<RouterProvider router={router} />);
  const user = userEvent.setup();
  if (lesson === "m1_l1") {
    await user.click(await screen.findByRole("radio", { name: "Both" }));
    await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "9"));
  } else await screen.findByRole("progressbar");
  for (let i = 0; i < 20 && !screen.queryByRole("heading", { name: heading }); i++) await user.click(next());
  await screen.findByRole("heading", { name: heading });
  return { user, router, ...utils };
}

describe("plan screen", () => {
  it("shows the cue, an empty box with a hint and requires words", async () => {
    const { user } = await goTo("Your plan for next time");
    expect(screen.getByText("If Mom asks the same question again,")).toBeInTheDocument();
    const box = screen.getByRole("textbox", { name: "then I'll say:" });
    expect(box).toHaveValue("");
    expect(screen.getByText("0 of 300")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/write a few words/i);
    expect(answers()).toHaveLength(0);
    expect(document.body.textContent).not.toMatch(/\{/);
  });

  it("prefills from the newest phrase saved in this lesson", async () => {
    await fetch("/api/phrases", {
      method: "POST",
      headers: { "X-Session-Token": token, "Content-Type": "application/json" },
      body: JSON.stringify({ text: "I'm right here.", source: "scenario", lessonId: "m1_l1" }),
    });
    await goTo("Your plan for next time");
    await waitFor(() => expect(screen.getByRole("textbox", { name: "then I'll say:" })).toHaveValue("I'm right here."));
  });

  it("prefills from the role-play best phrase, ahead of saved phrases", async () => {
    const router = createMemoryRouter(routes, { initialEntries: ["/lessons/m1_l1"] });
    render(<RouterProvider router={router} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("radio", { name: "Both" }));
    await waitFor(() => expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "9"));
    await fetch("/api/phrases", {
      method: "POST",
      headers: { "X-Session-Token": token, "Content-Type": "application/json" },
      body: JSON.stringify({ text: "A saved scenario phrase.", source: "scenario", lessonId: "m1_l1" }),
    });
    await screen.findByRole("heading", { name: "When Mom asks again" }).catch(() => undefined);
    for (let i = 0; i < 20 && !screen.queryByRole("button", { name: "Start practice" }); i++) {
      await user.click(next());
    }
    await user.click(screen.getByRole("button", { name: "Start practice" }));
    for (let round = 1; round <= 3; round++) {
      await user.type(await screen.findByRole("textbox", { name: "What would you say?" }), "I am here.");
      await user.click(screen.getByRole("button", { name: "Send" }));
      await screen.findByText("AI-generated");
      await user.click(screen.getByRole("button", { name: round < 3 ? "Next round" : "See your practice" }));
    }
    await user.click(await screen.findByRole("button", { name: "Continue" }));
    await user.click(next());
    await screen.findByRole("heading", { name: "Your plan for next time" });
    expect(screen.getByRole("textbox", { name: "then I'll say:" })).toHaveValue(
      "You sound worried. I'm right here. Want to sit with me for a minute?",
    );
  });

  it("Done posts once with reminderDownloaded false and shows the reset line", async () => {
    const { user } = await goTo("Your plan for next time");
    await user.type(screen.getByRole("textbox", { name: "then I'll say:" }), "You're safe.");
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(await screen.findByText(/Your plan is saved/)).toBeInTheDocument();
    expect(answers()).toHaveLength(1);
    expect(answers()[0]?.body).toEqual({
      screenId: "s8_plan",
      value: { response: "You're safe.", reminderDownloaded: false },
    });
    expect(screen.getByText(/One slow breath before I answer/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Done" })).toBeNull();
    expect(download).not.toHaveBeenCalled();
  });

  it("Remind me tomorrow posts reminderDownloaded true and downloads the file once", async () => {
    const { user } = await goTo("Your plan for next time");
    await user.type(screen.getByRole("textbox", { name: "then I'll say:" }), "You're safe.");
    await user.click(screen.getByRole("button", { name: "Remind me tomorrow" }));
    await screen.findByText(/Your plan is saved/);
    expect(answers()[0]?.body).toMatchObject({ value: { response: "You're safe.", reminderDownloaded: true } });
    expect(download).toHaveBeenCalledTimes(1);
  });

  it("shows the server's too-long and required messages", async () => {
    const { user } = await goTo("Your plan for next time");
    await user.type(screen.getByRole("textbox", { name: "then I'll say:" }), "x");
    api.injectError("POST", "/lessons/m1_l1/answers", 422, "invalid_screen_answer", {
      screen: "s8_plan",
      reason: "response_too_long",
    });
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/300 characters/);
    expect(download).not.toHaveBeenCalled();
  });

  it("do-now copies the phrase to the clipboard", async () => {
    const write = vi.fn(() => Promise.resolve());
    const open = vi.fn(() => null);
    vi.stubGlobal("open", open);
    const { user } = await goTo("Your plan for next time");
    Object.defineProperty(navigator, "clipboard", { value: { writeText: write }, configurable: true });
    await user.type(screen.getByRole("textbox", { name: "then I'll say:" }), "You're safe.");
    await user.click(screen.getByRole("button", { name: "Print and copy" }));
    expect(write).toHaveBeenCalledWith("You're safe.");
    expect(open).toHaveBeenCalled();
    expect(await screen.findByText(/blocked the print window|Copied/)).toBeInTheDocument();
  });

  it("is axe clean", async () => {
    await goTo("Your plan for next time");
    expect(await axe(document.body)).toHaveNoViolations();
  });
});

describe("wrap and completion", () => {
  async function toWrap() {
    return goTo("You did it");
  }

  it("shows the lines, hides phraseLine with no saved phrase, and needs all five ratings", async () => {
    const { user } = await toWrap();
    expect(screen.getByText(/New skill: handling repeated questions/)).toBeInTheDocument();
    expect(screen.queryByText(/Your phrase is saved to/)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Finish lesson" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/pick a number/i);
    expect(sent.some((c) => c.path.endsWith("/complete"))).toBe(false);
  });

  it("shows phraseLine when a phrase was saved for this lesson", async () => {
    await fetch("/api/phrases", {
      method: "POST",
      headers: { "X-Session-Token": token, "Content-Type": "application/json" },
      body: JSON.stringify({ text: "I'm right here.", source: "scenario", lessonId: "m1_l1" }),
    });
    await toWrap();
    expect(await screen.findByText("Your phrase is saved to Mom's page and care card.")).toBeInTheDocument();
  });

  it("sends all five ratings, completes, and shows tomorrow, the next lesson with reason and date", async () => {
    const { user } = await toWrap();
    for (const item of screen.getAllByRole("group")) {
      const radios = item.querySelectorAll("input");
      if (radios.length === 5) await user.click(radios[2] as HTMLInputElement);
    }
    await user.click(screen.getByRole("button", { name: "Finish lesson" }));
    expect(await screen.findByRole("heading", { name: "Lesson complete" })).toBeInTheDocument();
    expect(answers().at(-1)?.body).toEqual({
      screenId: "s9_wrap",
      value: { repeat: 3, accusations: 3, evenings: 3, refusal: 3, visits: 3 },
    });
    expect(sent.filter((c) => c.path.endsWith("/complete"))).toHaveLength(1);
    expect(screen.getByText(/Tomorrow: a quick check-in/)).toBeInTheDocument();
    expect(screen.getByText("Talking so it lands")).toBeInTheDocument();
    expect(screen.getByText(/Everyone starts here/)).toBeInTheDocument();
    expect(screen.getByText("Opens Jan 7")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Today" })).toHaveAttribute("href", "/today");
    expect(document.body.textContent).not.toMatch(/\{/);
  });

  it("retries after a failed completion without re-sending the ratings", async () => {
    const { user } = await toWrap();
    for (const item of screen.getAllByRole("group")) {
      const radios = item.querySelectorAll("input");
      if (radios.length === 5) await user.click(radios[0] as HTMLInputElement);
    }
    api.injectError("POST", "/lessons/m1_l1/complete", 500, "internal_error");
    await user.click(screen.getByRole("button", { name: "Finish lesson" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/went wrong/i);
    await user.click(screen.getByRole("button", { name: "Finish lesson" }));
    await screen.findByRole("heading", { name: "Lesson complete" });
    expect(answers().filter((a) => a.body["screenId"] === "s9_wrap")).toHaveLength(1);
  });

  it("a locked completion (423) shows a plain message", async () => {
    const { user } = await toWrap();
    for (const item of screen.getAllByRole("group")) {
      const radios = item.querySelectorAll("input");
      if (radios.length === 5) await user.click(radios[0] as HTMLInputElement);
    }
    api.injectError("POST", "/lessons/m1_l1/complete", 423, "lesson_locked", { unlockOn: "2026-01-07" });
    await user.click(screen.getByRole("button", { name: "Finish lesson" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/isn't open yet/i);
  });
});
