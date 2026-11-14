import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { clearToken, setToken } from "../../../api/session";
import { VISIT_LIMITS } from "../../../content/app/visit";
import { type FakeApi, installFakeApi } from "../../../test/fakeApi";
import { signIn } from "../../../test/fakeApp/core";
import { appFixture } from "../../../test/fakeApp/fixtures";
import VisitSheetPage from "./VisitSheetPage";
import { WithAppCopy } from "../../../test/withAppCopy";

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
let puts: Record<string, unknown>[];

beforeEach(() => {
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  clearToken();
  api = installFakeApi();
  setToken(signIn(api));
  puts = [];
  const inner = globalThis.fetch;
  vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "PUT" && String(input).endsWith("/visit-sheet") && typeof init.body === "string") {
      puts.push(JSON.parse(init.body) as Record<string, unknown>);
    }
    return inner(input, init);
  });
  vi.stubGlobal("print", vi.fn());
  window.print = vi.fn();
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  api.restore();
});

async function open(): Promise<ReturnType<typeof render>> {
  const view = render(
    <MemoryRouter>
      <WithAppCopy><VisitSheetPage /></WithAppCopy>
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { level: 1, name: /next doctor visit/i });
  return view;
}

function appState(): Record<string, unknown> {
  const state = api.sessions.get("fake-token-app");
  if (!state) throw new Error("no session");
  return state.app;
}

const questionList = (): HTMLElement => screen.getByRole("list", { name: "Our questions" });
const notes = (): HTMLTextAreaElement => screen.getByRole("textbox", { name: /Notes from family/ });
const saves = (): number => api.calls.filter((c) => c.method === "PUT" && c.path === "/visit-sheet").length;

describe("visit sheet page", () => {
  it("loads the sheet with the server title, footer and bank", async () => {
    await open();
    expect(screen.getByText(/Write down what you have noticed/)).toBeInTheDocument();
    const print = screen.getByTestId("visit-sheet-print");
    expect(within(print).getByText("Family observations, not a medical assessment.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add: What changes should we watch/ })).toBeInTheDocument();
    expect(screen.getByText("Saved privately to this session. No account, no name needed.")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\{/);
  });

  it("round trip: edits are saved and come back after a reload", async () => {
    const user = userEvent.setup();
    const first = await open();
    await user.type(screen.getByLabelText("Doctor or clinic"), "Dr. Park");
    fireEvent.change(screen.getByLabelText("Visit date"), { target: { value: "2026-02-03" } });
    fireEvent.change(notes(), { target: { value: "  Slept badly  " } });
    await user.click(screen.getByRole("button", { name: /Add: When should we plan the next visit/ }));
    await user.type(screen.getByLabelText("Your question"), "Is the new routine OK?");
    await user.click(screen.getByRole("button", { name: "Add your question" }));
    await user.click(screen.getByRole("button", { name: "Print or save as PDF" }));
    await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());
    const last = puts[puts.length - 1];
    expect(last).toEqual({
      doctor: "Dr. Park",
      visitDate: "2026-02-03",
      familyNotes: "  Slept badly  ",
      questions: [{ id: "q_next_visit" }, { text: "Is the new routine OK?" }],
    });
    first.unmount();
    await open();
    expect(screen.getByLabelText("Doctor or clinic")).toHaveValue("Dr. Park");
    expect(notes()).toHaveValue("  Slept badly  ");
    expect(within(questionList()).getAllByRole("listitem")).toHaveLength(2);
  });

  it("reorder and remove produce the right questions array", async () => {
    const user = userEvent.setup();
    await open();
    for (const id of ["q_tests", "q_safety", "q_next_visit"]) {
      const text = appFixture<{ bank: { id: string; text: string }[] }>("visit-sheet-empty").bank.find(
        (b) => b.id === id,
      )?.text as string;
      await user.click(screen.getByRole("button", { name: `Add: ${text}` }));
    }
    await user.type(screen.getByLabelText("Your question"), "Own one");
    await user.click(screen.getByRole("button", { name: "Add your question" }));
    // tests, safety, next_visit, own  ->  move the own one to the top, drop "safety"
    await user.click(screen.getByRole("button", { name: "Move up: Own one" }));
    await user.click(screen.getByRole("button", { name: "Move up: Own one" }));
    await user.click(screen.getByRole("button", { name: "Move up: Own one" }));
    await user.click(screen.getByRole("button", { name: /^Move down: Are there any tests/ }));
    await user.click(screen.getByRole("button", { name: /^Remove: Is there anything at home/ }));
    await user.click(screen.getByRole("button", { name: "Print or save as PDF" }));
    await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());
    expect(puts[puts.length - 1]?.["questions"]).toEqual([
      { text: "Own one" },
      { id: "q_tests" },
      { id: "q_next_visit" },
    ]);
  });

  it("a bank question is not offered twice", async () => {
    const user = userEvent.setup();
    await open();
    const button = (): HTMLElement | null =>
      screen.queryByRole("button", { name: /^Add: When should we plan the next visit/ });
    expect(button()).toBeInTheDocument();
    await user.click(button() as HTMLElement);
    expect(button()).toBeNull();
    await user.click(screen.getByRole("button", { name: /^Remove: When should we plan/ }));
    expect(button()).toBeInTheDocument();
  });

  it("a suggested note is appended to the notes, the user's words kept", async () => {
    appState()["visitSheet"] = appFixture("visit-sheet-filled");
    const user = userEvent.setup();
    await open();
    expect(notes()).toHaveValue("Slept badly");
    await user.click(screen.getByRole("button", { name: "Add to notes: At dinner" }));
    expect(notes()).toHaveValue("Slept badly\nAt dinner");
  });

  it("limits: 10 own questions, 300 characters, notes counter", async () => {
    const user = userEvent.setup();
    await open();
    expect(screen.getByLabelText("Your question")).toHaveAttribute("maxlength", String(VISIT_LIMITS.customQuestionLength));
    expect(notes()).toHaveAttribute("maxlength", String(VISIT_LIMITS.familyNotes));
    expect(screen.getByLabelText("Doctor or clinic")).toHaveAttribute("maxlength", String(VISIT_LIMITS.doctor));
    fireEvent.change(notes(), { target: { value: "abcd" } });
    expect(screen.getByText("4 / 2000")).toBeInTheDocument();
    for (let i = 0; i < VISIT_LIMITS.customQuestions; i += 1) {
      fireEvent.change(screen.getByLabelText("Your question"), { target: { value: `Mine ${i}` } });
      await user.click(screen.getByRole("button", { name: "Add your question" }));
    }
    fireEvent.change(screen.getByLabelText("Your question"), { target: { value: "One too many" } });
    expect(screen.getByRole("button", { name: "Add your question" })).toBeDisabled();
    expect(screen.getByText("You can add up to 10 questions of your own.")).toBeInTheDocument();
    // fill the rest of the 20 from the bank (8 questions available): 10 + 8 = 18, still addable
    for (const button of screen.getAllByRole("button", { name: /^Add: / })) await user.click(button);
    expect(within(questionList()).getAllByRole("listitem")).toHaveLength(18);
  });

  it("a full sheet of 20 questions offers no more", async () => {
    const empty = appFixture<{ bank: { id: string; text: string }[] }>("visit-sheet-empty");
    const questions = [
      ...Array.from({ length: 10 }, (_, i) => ({ id: null, text: `Mine ${i}`, custom: true })),
      ...empty.bank.slice(0, 8).map((b) => ({ id: b.id, text: b.text, custom: false })),
      { id: "extra_a", text: "Extra A", custom: false },
      { id: "extra_b", text: "Extra B", custom: false },
    ];
    appState()["visitSheet"] = {
      ...empty,
      bank: [...empty.bank, { id: "q_more", text: "One more bank question" }],
      questions,
    };
    await open();
    expect(screen.getByText(/holds up to 20 questions/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add: One more bank question" })).toBeDisabled();
  });

  it("autosave waits 800 ms of quiet, then saves once", async () => {
    await open();
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    fireEvent.change(screen.getByLabelText("Doctor or clinic"), { target: { value: "Dr" } });
    await act(async () => {
      vi.advanceTimersByTime(500);
    });
    fireEvent.change(screen.getByLabelText("Doctor or clinic"), { target: { value: "Dr. Lee" } });
    await act(async () => {
      vi.advanceTimersByTime(799);
    });
    expect(saves()).toBe(0);
    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    vi.useRealTimers();
    await waitFor(() => expect(saves()).toBe(1));
    expect(puts[0]?.["doctor"]).toBe("Dr. Lee");
    await screen.findByText("Saved");
  });

  it("blur saves at once and print flushes pending edits first", async () => {
    await open();
    const doctor = screen.getByLabelText("Doctor or clinic");
    fireEvent.change(doctor, { target: { value: "Dr. Kim" } });
    fireEvent.blur(doctor);
    await waitFor(() => expect(saves()).toBe(1));
    fireEvent.change(notes(), { target: { value: "Before print" } });
    expect(saves()).toBe(1);
    fireEvent.click(screen.getByRole("button", { name: "Print or save as PDF" }));
    await waitFor(() => expect(window.print).toHaveBeenCalledTimes(1));
    expect(saves()).toBe(2);
    expect(puts[1]?.["familyNotes"]).toBe("Before print");
  });

  it("leaving the page sends pending edits", async () => {
    const view = await open();
    fireEvent.change(notes(), { target: { value: "Leaving" } });
    view.unmount();
    await waitFor(() => expect(saves()).toBe(1));
  });

  it("a failed save keeps the words and offers a retry that works", async () => {
    const user = userEvent.setup();
    await open();
    api.injectError("PUT", "/visit-sheet", 422, "invalid_visit_sheet", { field: "doctor" });
    const doctor = screen.getByLabelText("Doctor or clinic");
    fireEvent.change(doctor, { target: { value: "Dr. Lee" } });
    fireEvent.blur(doctor);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Not saved yet/);
    expect(alert).not.toHaveTextContent("Dr. Lee");
    expect(doctor).toHaveValue("Dr. Lee");
    await user.click(screen.getByRole("button", { name: "Try saving again" }));
    await screen.findByText("Saved");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("unknown_visit_question has its own warm message", async () => {
    await open();
    api.injectError("PUT", "/visit-sheet", 422, "unknown_visit_question", { questionIds: ["nope"] });
    fireEvent.change(notes(), { target: { value: "x" } });
    fireEvent.blur(notes());
    expect(await screen.findByRole("alert")).toHaveTextContent(/no longer on the list/);
  });

  it("the preview shows prepared-by from the profile and the typed date", async () => {
    appState()["profile"] = {
      ...appFixture<Record<string, unknown>>("profile-filled"),
      caregiverFirstName: "Sam",
    };
    await open();
    const print = screen.getByTestId("visit-sheet-print");
    await within(print).findByText("Prepared by Sam");
    fireEvent.change(screen.getByLabelText("Visit date"), { target: { value: "2026-02-03" } });
    expect(within(print).getByText("Feb 3, 2026")).toBeInTheDocument();
  });

  it("shows a retry block when loading fails, and retries", async () => {
    api.injectError("GET", "/visit-sheet", 500, "server_error");
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <WithAppCopy><VisitSheetPage /></WithAppCopy>
      </MemoryRouter>,
    );
    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { level: 1, name: /next doctor visit/i });
  });

  it("logs nothing to the console", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((m) => vi.spyOn(console, m));
    const user = userEvent.setup();
    await open();
    fireEvent.change(notes(), { target: { value: "private words" } });
    await user.click(screen.getByRole("button", { name: "Print or save as PDF" }));
    await screen.findByText("Saved");
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
    spies.forEach((s) => s.mockRestore());
  });

  it("has no axe violations", async () => {
    const { container } = await open();
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("print CSS", () => {
  const css = readFileSync(resolve(__dirname, "VisitSheet.module.css"), "utf-8");
  it("prints one Letter page, black and white, only the sheet", () => {
    expect(css).toMatch(/@page\s*{[^}]*size:\s*Letter/);
    const print = css.slice(css.indexOf("@media print"));
    expect(print).toMatch(/body \*\s*{\s*visibility:\s*hidden/);
    expect(print).toMatch(/\.sheet,\s*\.sheet \*\s*{\s*visibility:\s*visible/);
    expect(print).toMatch(/color:\s*#000/);
    expect(print).not.toMatch(/background:\s*var\(--(accent|warning|success)/);
  });
});
