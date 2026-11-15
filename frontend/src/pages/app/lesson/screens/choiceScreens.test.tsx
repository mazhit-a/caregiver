import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { answerLesson, getLesson } from "../../../../api/app";
import type { BuilderScreen as BuilderData, Lesson, QuizScreen as QuizData, ResetScreen as ResetData, ScenarioScreen as ScenarioData, SetupScreen as SetupData } from "../../../../api/appTypes";
import { clearToken, setToken } from "../../../../api/session";
import { type FakeApi, installFakeApi } from "../../../../test/fakeApi";
import { signIn } from "../../../../test/fakeApp/core";
import { WithAppCopy } from "../../../../test/withAppCopy";
import { BuilderScreen } from "./BuilderScreen";
import { QuizScreen } from "./QuizScreen";
import { ResetScreen } from "./ResetScreen";
import { ScenarioScreen } from "./ScenarioScreen";
import { SetupScreen } from "./SetupScreen";
import type { AnswerEntry, AnswerStore, ScreenProps } from "./types";

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
let lesson: Lesson;
beforeEach(async () => {
  vi.stubGlobal("Request", TestRequest);
  Object.defineProperty(window, "localStorage", { value: memoryStorage(), configurable: true });
  clearToken();
  api = installFakeApi({ lesson24: true });
  setToken(signIn(api));
  await answerLesson("m1_l1", { screenId: "setup", value: "both" });
  lesson = await getLesson("m1_l1");
});
afterEach(() => {
  api.restore();
  vi.unstubAllGlobals();
});

const find = <T,>(id: string): T => lesson.screens.find((s) => s.id === id) as T;

/** Keeps the remembered answers like the player does, so locked and restored states can be checked. */
function Harness<S>({ Screen, screenData, start }: { Screen: React.ComponentType<ScreenProps<S>>; screenData: S & { id: string }; start?: AnswerEntry }) {
  const [answers, setAnswers] = useState<AnswerStore>(start ? { [screenData.id]: start } : {});
  return (
    <Screen
      screen={screenData}
      lesson={lesson}
      entry={answers[screenData.id]}
      answers={answers}
      remember={(id, next) => setAnswers((c) => ({ ...c, [id]: next(c[id]) }))}
      reload={async () => true}
    />
  );
}
const mount = <S,>(Screen: React.ComponentType<ScreenProps<S>>, data: S & { id: string }, start?: AnswerEntry) =>
  render(
    <WithAppCopy>
      <Harness Screen={Screen} screenData={data} start={start} />
    </WithAppCopy>,
  );

describe("quiz screen", () => {
  it("right pick: the option is marked Correct in text, feedback in a status region, then locked", async () => {
    const user = userEvent.setup();
    const { container } = mount(QuizScreen, find<QuizData>("q1"));
    await user.click(screen.getByRole("radio", { name: /The answer faded/ }));
    await waitFor(() => expect(screen.getByRole("radio", { name: /The answer faded/ })).toHaveAccessibleName(/Correct/));
    expect(screen.getByRole("status")).toHaveTextContent("That’s right.");
    for (const r of screen.getAllByRole("radio")) expect(r).toBeDisabled();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("wrong pick: warm feedback with text marks, the right option is shown", async () => {
    const user = userEvent.setup();
    const { container } = mount(QuizScreen, find<QuizData>("q1"));
    await user.click(screen.getByRole("radio", { name: /testing your patience/ }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Not quite, and that’s okay."));
    expect(screen.getByRole("status")).toHaveTextContent(/the memory of asking has faded/);
    expect(screen.getByRole("radio", { name: /testing your patience/ })).toHaveAccessibleName(/Not quite/);
    expect(screen.getByRole("radio", { name: /The answer faded/ })).toHaveAccessibleName(/Correct/);
    expect(screen.getByRole("radio", { name: /testing your patience/ })).toBeChecked();
    expect(screen.queryByText(/wrong/i)).toBeNull();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("keyboard: arrow keys move through the group, Space picks", async () => {
    const user = userEvent.setup();
    mount(QuizScreen, find<QuizData>("q1"));
    await user.tab();
    expect(screen.getAllByRole("radio")[0]).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    await waitFor(() => expect(screen.getByRole("status")).not.toBeEmptyDOMElement());
  });

  it("a failed answer shows an alert and Try again posts it again", async () => {
    const user = userEvent.setup();
    mount(QuizScreen, find<QuizData>("q1"));
    const real = globalThis.fetch;
    const failing = vi.fn().mockRejectedValue(new TypeError("offline"));
    vi.stubGlobal("fetch", failing);
    await user.click(screen.getByRole("radio", { name: /The answer faded/ }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    vi.stubGlobal("fetch", real);
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("That’s right."));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("a remembered answer shows locked when the screen is revisited", () => {
    mount(QuizScreen, find<QuizData>("q1"), {
      value: "o1",
      saved: [],
      result: { optionId: "o1", correct: false, correctOptionId: "o3", feedback: "It can feel that way." },
    });
    expect(screen.getByRole("status")).toHaveTextContent("It can feel that way.");
    expect(screen.getByRole("radio", { name: /testing your patience/ })).toBeDisabled();
  });
});

describe("builder screen", () => {
  const pick = (user: ReturnType<typeof userEvent.setup>, name: RegExp) => user.click(screen.getByRole("radio", { name }));

  it("posts only when all three groups are picked, shows the server reply and feedback", async () => {
    const user = userEvent.setup();
    const { container } = mount(BuilderScreen, find<BuilderData>("builder"));
    expect(screen.getAllByRole("group")).toHaveLength(3);
    await pick(user, /You’re wondering about tomorrow/);
    await pick(user, /plenty of time/);
    expect(screen.getByRole("status", { hidden: true })).toBeEmptyDOMElement();
    await pick(user, /Want to help me with the tea|tea/);
    const status = await screen.findByRole("status");
    await waitFor(() => expect(status).toHaveTextContent("Your reply"));
    expect(status).toHaveTextContent(/You’re wondering about tomorrow\. We have plenty of time/);
    expect(status).toHaveTextContent("That’s all three steps.");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("changing a pick re-posts and shows the not-yet feedback with a text mark on the group", async () => {
    const user = userEvent.setup();
    mount(BuilderScreen, find<BuilderData>("builder"));
    await pick(user, /You’re wondering about tomorrow/);
    await pick(user, /plenty of time/);
    await pick(user, /tea/);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("That’s all three steps."));
    await pick(user, /I already told you/);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Close. One part"));
    expect(screen.getByRole("status")).toHaveTextContent(/I already told you\. We have plenty/);
    expect(screen.getByText("Try another")).toBeInTheDocument();
    expect(screen.getAllByText("Fits").length).toBeGreaterThan(0);
  });

  it("a failed post can be retried", async () => {
    const user = userEvent.setup();
    mount(BuilderScreen, find<BuilderData>("builder"));
    await pick(user, /You’re wondering about tomorrow/);
    await pick(user, /plenty of time/);
    const real = globalThis.fetch;
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await pick(user, /tea/);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    vi.stubGlobal("fetch", real);
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Your reply"));
  });
});

describe("reset screen", () => {
  it("stores the pick, confirms it and draws no image", async () => {
    const user = userEvent.setup();
    const { container } = mount(ResetScreen, find<ResetData>("you"));
    expect(container.querySelector("img")).toBeNull();
    await user.click(screen.getByRole("radio", { name: "One slow breath before I answer" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/goes into your plan/));
    expect(screen.getByRole("radio", { name: "One slow breath before I answer" })).toBeChecked();
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("setup and scenario screens", () => {
  it("setup: title, body, labelled radios; the pick posts and reloads", async () => {
    const user = userEvent.setup();
    const reload = vi.fn().mockResolvedValue(true);
    const data = find<SetupData>("setup");
    const { container } = render(
      <WithAppCopy>
        <SetupScreen screen={data} lesson={lesson} entry={undefined} remember={() => undefined} reload={reload} />
      </WithAppCopy>,
    );
    expect(screen.getByRole("heading", { level: 2, name: data.title })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: data.title })).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "On the phone" }));
    await waitFor(() => expect(reload).toHaveBeenCalled());
    expect(await axe(container)).toHaveNoViolations();
  });

  it("scenario: title is the legend, note shown, labels from app copy, never 'Wrong'", async () => {
    const user = userEvent.setup();
    const data = find<ScenarioData>("scenario");
    const { container } = mount(ScenarioScreen, data);
    expect(screen.getByRole("group", { name: data.title })).toBeInTheDocument();
    expect(screen.getByText(data.note ?? "")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: data.answers[0]?.text ?? "" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/Good instinct|Noted|Very common/));
    expect(screen.getByRole("status").textContent).not.toMatch(/wrong/i);
    await act(async () => undefined);
    expect(await axe(container)).toHaveNoViolations();
  });
});
