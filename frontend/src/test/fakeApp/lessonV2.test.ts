import { afterEach, beforeEach, describe, expect, it } from "vitest";
import * as A from "../../api/app";
import { classifyAppError } from "../../api/errors";
import { clearToken, setToken } from "../../api/session";
import { type FakeApi, installFakeApi } from "../fakeApi";
import { signIn } from "./core";

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
  api = installFakeApi({ lesson24: true });
  setToken(signIn(api));
});
afterEach(() => api.restore());

const failure = async (p: Promise<unknown>): Promise<ReturnType<typeof classifyAppError>> =>
  classifyAppError(await p.then(() => undefined, (e: unknown) => e));

const ids = (lesson: { screens: { id: string }[] }): string[] => lesson.screens.map((s) => s.id);

describe("24-screen lesson fake", () => {
  it("serves intro and setup first, then the whole lesson after the setup answer", async () => {
    const first = await A.getLesson("m1_l1");
    expect(first.variant).toBeNull();
    expect(first.screens.map((s) => s.type)).toEqual(["intro", "setup"]);
    expect(first.screenCount).toBe(24);

    const answered = await A.answerLesson("m1_l1", { screenId: "setup", value: "phone" });
    expect(answered).toMatchObject({ type: "setup", result: { variant: "phone" } });
    const lesson = await A.getLesson("m1_l1");
    expect(lesson.variant).toBe("phone");
    expect(lesson.screens).toHaveLength(24);
    expect(ids(lesson).slice(0, 3)).toEqual(["intro", "setup", "scenario"]);
    expect(lesson.screens.map((s) => s.type)).not.toContain("unknown");
  });

  it("rejects an unknown setup option and an unknown screen", async () => {
    expect(await failure(A.answerLesson("m1_l1", { screenId: "setup", value: "nope" }))).toMatchObject({
      kind: "validation",
    });
    expect(await failure(A.answerLesson("m1_l1", { screenId: "ghost", value: "x" }))).toMatchObject({
      kind: "validation",
    });
  });

  it("every variant serves 24 screens, the same ids, no unfilled placeholder", async () => {
    let reference: string[] | null = null;
    for (const variant of ["in_person", "phone", "both", "not_yet"]) {
      await A.answerLesson("m1_l1", { screenId: "setup", value: variant });
      const lesson = await A.getLesson("m1_l1");
      reference ??= ids(lesson);
      expect(ids(lesson)).toEqual(reference);
      expect(JSON.stringify(lesson)).not.toMatch(/\{[A-Za-z]+\}/);
    }
  });

  it("quiz: the server decides, and reveals the right option after a pick", async () => {
    await A.answerLesson("m1_l1", { screenId: "setup", value: "in_person" });
    const wrong = await A.answerLesson("m1_l1", { screenId: "q1", value: "o1" });
    expect(wrong.result).toMatchObject({ optionId: "o1", correct: false, correctOptionId: "o3" });
    const right = await A.answerLesson("m1_l1", { screenId: "q1", value: "o3" });
    expect(right.result).toMatchObject({ correct: true, correctOptionId: "o3" });
    expect(await failure(A.answerLesson("m1_l1", { screenId: "q1", value: "o9" }))).toMatchObject({
      kind: "validation",
    });
  });

  it("scenario: verdict by answer, savePhrase only for the best one", async () => {
    await A.answerLesson("m1_l1", { screenId: "setup", value: "both" });
    const best = await A.answerLesson("m1_l1", { screenId: "scenario", value: "a4" });
    expect(best.result).toMatchObject({ verdict: "best", savePhrase: true });
    const hard = await A.answerLesson("m1_l1", { screenId: "scenario", value: "a3" });
    expect(hard.result).toMatchObject({ verdict: "try_again", savePhrase: false });
  });

  it("builder: the reply is assembled by the server from the picks", async () => {
    await A.answerLesson("m1_l1", { screenId: "setup", value: "in_person" });
    const good = await A.answerLesson("m1_l1", { screenId: "builder", value: ["o1", "o2", "o1"] });
    expect(good.result).toMatchObject({ allCorrect: true, groups: [{ correct: true }, { correct: true }, { correct: true }] });
    expect(String(good.result["reply"])).toContain("wondering about tomorrow");
    const partly = await A.answerLesson("m1_l1", { screenId: "builder", value: ["o2", "o2", "o1"] });
    expect(partly.result).toMatchObject({ allCorrect: false });
    expect(await failure(A.answerLesson("m1_l1", { screenId: "builder", value: ["o1"] }))).toMatchObject({
      kind: "validation",
    });
  });

  it("reset pick reaches the plan answer", async () => {
    await A.answerLesson("m1_l1", { screenId: "setup", value: "in_person" });
    const reset = await A.answerLesson("m1_l1", { screenId: "you", value: "r2" });
    expect(reset.result).toEqual({ optionId: "r2", text: "say the first words slowly" });
    const plan = await A.answerLesson("m1_l1", { screenId: "plan", value: { response: "x" } });
    expect((plan.result["ifThen"] as { reset: string }).reset).toBe("say the first words slowly");
  });

  it("progress can reach screen 24 and survives a reload", async () => {
    await A.answerLesson("m1_l1", { screenId: "setup", value: "phone" });
    expect((await A.putLessonProgress("m1_l1", 12)).step).toBe(12);
    expect((await A.getLesson("m1_l1")).progress.step).toBe(12);
    expect(await failure(A.putLessonProgress("m1_l1", 24))).toMatchObject({ kind: "validation" });
  });

  it("is off by default: lesson 1 stays the old 9-screen lesson", async () => {
    api.scenario.lesson24 = false;
    expect((await A.getLesson("m1_l1")).screens.map((s) => s.type)).toEqual(["setup_question"]);
  });
});
