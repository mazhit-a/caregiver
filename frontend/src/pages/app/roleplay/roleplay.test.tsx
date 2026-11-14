import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../../../api/session";
import type { RoleplayFinish } from "../../../api/appTypes";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import { RoleplayRoom } from "./RoleplayRoom";

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
const done = vi.fn<(finish: RoleplayFinish | null) => void>();

beforeEach(() => {
  vi.stubGlobal("Request", TestRequest);
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  Object.defineProperty(window, "sessionStorage", { value: memoryStorage(), configurable: true });
  window.scrollTo = vi.fn();
  clearToken();
  api = installFakeApi();
  setToken(signIn(api));
  done.mockReset();
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

function mount() {
  const router = createMemoryRouter(
    [{ path: "/", element: <RoleplayRoom lessonId="m1_l1" context="lesson" onDone={done} /> }],
    { initialEntries: ["/"] },
  );
  return render(<RouterProvider router={router} />);
}

interface Sent {
  method: string;
  path: string;
  body: Record<string, unknown>;
}
function sent(): Sent[] {
  return vi.mocked(fetch).mock.calls.map(([input, init]) => ({
    method: (init?.method ?? "GET").toUpperCase(),
    path: String(input).replace(/^\/api/, ""),
    body: typeof init?.body === "string" ? (JSON.parse(init.body) as Record<string, unknown>) : {},
  }));
}
const turnCalls = () => sent().filter((c) => /\/roleplay\/[^/]+\/turn$/.test(c.path));

const box = () => screen.findByRole("textbox", { name: "What would you say?" });
const sendBtn = () => screen.getByRole("button", { name: "Send" });

async function playRound(text: string) {
  const user = userEvent.setup();
  await user.type(await box(), text);
  await user.click(sendBtn());
  await screen.findByText("AI-generated");
  return user;
}

describe("RoleplayRoom (AI path)", () => {
  it("plays three rounds, then shows the server summary and saves the best phrase", async () => {
    mount();
    expect(await screen.findByText(/AI practice partner/)).toBeInTheDocument();
    expect(screen.getByText("Round 1 of 3")).toBeInTheDocument();
    let user = await playRound("You sound worried.");
    expect(screen.getByText("3 of 3", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("You sound worried. I'm here. Want some tea?", { exact: false })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next round" }));
    expect(await screen.findByText("Round 2 of 3")).toBeInTheDocument();
    user = await playRound("I am here.");
    await user.click(screen.getByRole("button", { name: "Next round" }));
    await screen.findByText("Round 3 of 3");
    user = await playRound("Let's sit together.");
    await user.click(screen.getByRole("button", { name: "See your practice" }));
    expect(await screen.findByRole("heading", { name: "Your practice" })).toBeInTheDocument();
    expect(screen.getByText("First try: 3 of 3 · Last try: 3 of 3")).toBeInTheDocument();
    expect(screen.getByText(/I'm right here/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/Saved to your phrases\./)).toBeInTheDocument();
    expect(screen.getByText(/Saved privately to this session\. No account, no name needed\./)).toBeInTheDocument();
    const saves = sent().filter((c) => c.path === "/phrases" && c.method === "POST");
    expect(saves).toHaveLength(1);
    expect(saves[0]?.body).toMatchObject({ source: "roleplay", lessonId: "m1_l1" });
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(done).toHaveBeenCalledWith(expect.objectContaining({ bestPhrase: expect.any(String) }));
    expect(turnCalls()).toHaveLength(3);
  });

  it("sends at most the last three previous turns as parent, caregiver and score", async () => {
    mount();
    let user = await playRound("one");
    for (const word of ["two", "three"]) {
      await user.click(screen.getByRole("button", { name: "Next round" }));
      user = await playRound(word);
    }
    const [first, second, third] = turnCalls();
    expect(first?.body["previousTurns"]).toEqual([]);
    expect(second?.body["previousTurns"]).toEqual([
      { parent: "When are you coming on Saturday?", caregiver: "one", score: 3 },
    ]);
    expect((third?.body["previousTurns"] as unknown[]).length).toBe(2);
    expect(third?.body["round"]).toBe(3);
  });

  it("limits the reply to 500 characters and blocks empty or blank replies", async () => {
    mount();
    const user = userEvent.setup();
    const field = await box();
    expect(field).toHaveAttribute("maxlength", "500");
    await user.click(sendBtn());
    await user.type(field, "   ");
    await user.click(sendBtn());
    expect(turnCalls()).toHaveLength(0);
    await user.click(field);
    await user.paste("a".repeat(600));
    expect((field as HTMLTextAreaElement).value).toHaveLength(500);
    expect(screen.getByText("500 of 500 characters")).toBeInTheDocument();
  });

  it("shows score, goals and tip exactly as the server returned them (medical: score 0, fixed tip)", async () => {
    api.scenario.roleplayMode = ["medical"];
    mount();
    await playRound("Should she take more pills?");
    expect(screen.getByText(/0 of 3/)).toBeInTheDocument();
    expect(screen.getByText(/ask Mom's doctor or pharmacist/)).toBeInTheDocument();
    expect(screen.queryByText("Try:")).not.toBeInTheDocument();
  });

  it("keeps the reply and offers Try again when a turn fails", async () => {
    mount();
    const user = userEvent.setup();
    await user.type(await box(), "hello there");
    api.injectError("POST", "/roleplay/*", 500, "internal_error");
    await user.click(sendBtn());
    expect(await screen.findByText(/The practice partner isn't available right now/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "What would you say?" })).toHaveValue("hello there");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("AI-generated")).toBeInTheDocument();
  });

  it("offers retry when the start fails", async () => {
    api.injectError("POST", "/roleplay/start", 429, "rate_limited");
    mount();
    expect(await screen.findByText("Practice didn't start")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await box()).toBeInTheDocument();
  });

  it("starts a new run on Practice again", async () => {
    mount();
    let user = await playRound("a");
    await user.click(screen.getByRole("button", { name: "Next round" }));
    user = await playRound("b");
    await user.click(screen.getByRole("button", { name: "Next round" }));
    user = await playRound("c");
    await user.click(screen.getByRole("button", { name: "See your practice" }));
    await user.click(await screen.findByRole("button", { name: "Practice again" }));
    expect(await screen.findByText("Round 1 of 3")).toBeInTheDocument();
    expect(sent().filter((c) => c.path === "/roleplay/start")).toHaveLength(2);
  });

  it("never lets the reply text leave the role-play calls or reach storage, title, history or console", async () => {
    const secret = "unique-secret-reply-text";
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((m) => vi.spyOn(console, m));
    const { unmount } = mount();
    const user = await playRound(secret);
    for (const store of [localStorage, sessionStorage]) {
      for (let i = 0; i < store.length; i += 1) expect(store.getItem(store.key(i) ?? "")).not.toContain(secret);
    }
    expect(document.title).not.toContain(secret);
    expect(JSON.stringify(window.history.state)).not.toContain(secret);
    expect(window.location.href).not.toContain(secret);
    for (const call of sent()) {
      const carries = JSON.stringify(call.body).includes(secret) || call.path.includes(secret);
      if (carries) expect(call.path).toMatch(/^\/roleplay\/[^/]+\/turn$/);
    }
    await user.click(screen.getByRole("button", { name: "Next round" }));
    unmount();
    mount();
    expect(await screen.findByText("Round 1 of 3")).toBeInTheDocument();
    expect(screen.queryByText(secret)).not.toBeInTheDocument();
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("shows the labels and has no axe violations in the reply and coach states", async () => {
    const { container } = mount();
    await box();
    expect(screen.getByText(/We teach and organize/)).toBeInTheDocument();
    expect(screen.getByText(/This conversation isn't saved/)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
    await playRound("You sound worried.");
    expect(await axe(container)).toHaveNoViolations();
    await waitFor(() => expect(screen.getByRole("button", { name: "Next round" })).toBeInTheDocument());
  });
});

describe("coach source rules", () => {
  const read = (p: string) => readFileSync(resolve(__dirname, p), "utf8");
  const files = [
    "RoleplayRoom.tsx",
    "../../../components/coach/CoachPanel.tsx",
    "../../../components/coach/SummaryCard.tsx",
    "../../../components/coach/ReplyBox.tsx",
    "../lesson/RoleplayScreen.tsx",
  ];

  it("has no console calls", () => {
    for (const f of files) expect(read(f)).not.toMatch(/console\./);
  });

  it("does no arithmetic over goals or scores", () => {
    for (const f of files) {
      const src = read(f);
      expect(src).not.toMatch(/goals[^\n]*\.(filter|reduce)\(/);
      expect(src).not.toMatch(/score\s*[-+*/]\s*\d|[-+]\s*score\b/);
    }
  });

  it("never touches storage or the URL", () => {
    for (const f of files) expect(read(f)).not.toMatch(/localStorage|sessionStorage|history\.|document\.title/);
  });
});

describe("RoleplayScreen in the lesson player", () => {
  it("shows intro, goals and labels, then starts the room on request", async () => {
    const { RoleplayScreen } = await import("../lesson/RoleplayScreen");
    const { appFixture } = await import("../../../test/fakeApp/fixtures");
    const lesson = appFixture<{ screens: { type: string }[]; id: string }>("lesson-m1_l1-both");
    const data = lesson.screens.find((s) => s.type === "roleplay") as never;
    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: (
            <RoleplayScreen screen={data} lesson={lesson as never} entry={undefined} remember={vi.fn()} reload={async () => true} />
          ),
        },
      ],
      { initialEntries: ["/"] },
    );
    render(<RouterProvider router={router} />);
    expect(screen.getByText(/Mom is an AI practice partner/)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Goals" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Start practice" }));
    expect(await box()).toBeInTheDocument();
  });
});
