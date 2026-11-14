import { afterEach, beforeEach, describe, expect, it } from "vitest";
import * as A from "../../api/app";
import { classifyAppError } from "../../api/errors";
import { clearToken, setToken } from "../../api/session";
import { type FakeApi, installFakeApi } from "../fakeApi";
import { signIn } from "./core";
import { appFixture } from "./fixtures";
import { type FakeRoute, registerFakeArea, route, unregisterFakeArea } from "./registry";

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

const failure = async (p: Promise<unknown>): Promise<ReturnType<typeof classifyAppError>> =>
  classifyAppError(await p.then(() => undefined, (e: unknown) => e));

describe("app fake: every endpoint answers with the captured shape", () => {
  it("copy, today in each state, plan", async () => {
    expect((await A.getAppCopy()).nav.profilePage).toBe("Mom's page");
    for (const state of ["fresh", "after_lesson_1", "day2", "nudge", "all_done"] as const) {
      api.scenario.today = state;
      expect((await A.getToday()).title).toMatch(/^Today with /);
    }
    api.scenario.today = "day2";
    expect((await A.getToday()).checkIn?.planId).toBe("m1_l1");
    api.scenario.today = "nudge";
    expect((await A.getToday()).careCardNudge?.newPhraseCount).toBe(1);
    expect((await A.getPlan()).modules.length).toBeGreaterThan(0);
  });

  it("demo controls off: no block on Today, /demo answers 404", async () => {
    api.scenario.demoControls = false;
    api.scenario.today = "day2";
    expect((await A.getToday()).demo).toBeNull();
    expect(await failure(A.getDemo())).toEqual({ kind: "not_found" });
    expect(await failure(A.demoNextDay())).toEqual({ kind: "not_found" });
  });

  it("demo next day moves after_lesson_1 to day2", async () => {
    api.scenario.today = "after_lesson_1";
    expect((await A.getDemo()).demoControls).toBe(true);
    await A.demoNextDay();
    expect((await A.getToday()).checkIn).not.toBeNull();
    expect((await A.demoJumpToRenewal()).subscriptionStatus).toBe("demo");
    expect(await failure(A.demoFailNextPayment())).toEqual({ kind: "conflict", code: "not_a_stripe_subscription" });
  });

  it("lesson 1: variant by the setup answer, step by the progress call, then answers and complete", async () => {
    const first = await A.getLesson("m1_l1");
    expect(first.variant).toBeNull();
    expect(first.screens.map((s) => s.type)).toEqual(["setup_question"]);
    const setup = first.screens[0];
    if (setup?.type !== "setup_question") throw new Error("setup first");
    const answered = await A.answerLesson("m1_l1", { screenId: setup.id, value: "phone" });
    expect(answered.result).toEqual({ variant: "phone" });
    const lesson = await A.getLesson("m1_l1");
    expect(lesson.variant).toBe("phone");
    expect(lesson.screens.length).toBeGreaterThan(5);
    expect((await A.putLessonProgress("m1_l1", 3)).step).toBe(3);
    expect((await A.getLesson("m1_l1")).progress.step).toBe(3);
    const scenario = lesson.screens.find((s) => s.type === "scenario");
    if (scenario?.type !== "scenario") throw new Error("scenario");
    const first_answer = scenario.answers[0];
    const result = await A.answerLesson("m1_l1", { screenId: scenario.id, value: first_answer?.id });
    expect((result.result as { verdict: string }).verdict).toBeTruthy();
    const plan = lesson.screens.find((s) => s.type === "plan");
    const planned = await A.answerLesson("m1_l1", { screenId: plan?.id ?? "", value: { response: "x" } });
    expect(planned.result).toHaveProperty("reminder");
    const wrap = lesson.screens.find((s) => s.type === "wrap");
    const rated = await A.answerLesson("m1_l1", { screenId: wrap?.id ?? "", value: { repeat: 3 } });
    expect(rated.result).toMatchObject({ saved: true });
    expect((await A.completeLesson("m1_l1")).nextLesson?.id).toBe("m1_l2");
  });

  it("lessons: 423 locked with unlockOn, 404 unknown, 422 bad option or step", async () => {
    expect(await failure(A.getLesson("m1_l2"))).toEqual({ kind: "lesson_locked", unlockOn: "2026-01-07" });
    expect(await failure(A.getLesson("nope"))).toEqual({ kind: "not_found" });
    expect(await failure(A.answerLesson("m1_l1", { screenId: "s1_setup", value: "nope" }))).toMatchObject({
      kind: "validation",
      code: "invalid_screen_answer",
    });
    expect(await failure(A.putLessonProgress("m1_l1", 99))).toMatchObject({ kind: "validation" });
    api.scenario.today = "all_done";
    expect((await A.getLesson("m1_l2")).id).toBe("m1_l2");
    expect((await A.getLesson("m1_l5")).id).toBe("m1_l5");
  });

  it("role-play: ai, medical, fallback (stays), crisis, emergency; finish; errors", async () => {
    const start = await A.startRoleplay("m1_l1", "lesson");
    const turn = (round: number, reply = "You sound worried. I'm here.") =>
      A.submitTurn(start.runId, { round, reply, previousTurns: [] });
    api.scenario.roleplayMode = ["ai", "medical", "fallback", "ai"];
    expect((await turn(1)).coach?.score).toBe(3);
    expect((await turn(2)).coach?.flags).toEqual(["medical"]);
    expect((await turn(3)).mode).toBe("fallback");
    expect((await A.finishRoleplay(start.runId, [])).mode).toBe("fallback");

    const again = await A.startRoleplay("m1_l1", "lesson");
    api.scenario.roleplayMode = ["crisis"];
    const safety = await A.submitTurn(again.runId, { round: 1, reply: "x y z", previousTurns: [] });
    expect(safety).toMatchObject({ mode: "safety", kind: "crisis" });
    expect(safety.resources.length).toBeGreaterThan(0);
    api.scenario.roleplayMode = ["emergency"];
    expect((await A.submitTurn(again.runId, { round: 1, reply: "x y z", previousTurns: [] })).kind).toBe("emergency");

    expect(await failure(A.submitTurn("missing", { round: 1, reply: "hi", previousTurns: [] }))).toEqual({ kind: "not_found" });
    const third = await A.startRoleplay("m1_l1", "practice_round");
    expect(third.roundsTotal).toBeLessThan(start.roundsTotal);
    expect(await failure(A.submitTurn(third.runId, { round: 1, reply: "  ", previousTurns: [] }))).toMatchObject({ kind: "validation" });
    expect(await failure(A.submitTurn(third.runId, { round: 2, reply: "hi", previousTurns: [] }))).toMatchObject({ kind: "validation", code: "round_mismatch" });
  });

  it("phrases: list, save (201), delete (204), delete again is 404", async () => {
    expect((await A.listPhrases()).phrases).toEqual([]);
    const saved = await A.savePhrase({ text: "I'm here.", source: "roleplay", lessonId: "m1_l1" });
    expect(saved.text).toBe("I'm here.");
    expect((await A.listPhrases()).phrases).toHaveLength(1);
    await expect(A.deletePhrase(saved.id)).resolves.toBeUndefined();
    expect(await failure(A.deletePhrase(saved.id))).toEqual({ kind: "not_found" });
    expect(await failure(A.savePhrase({ text: "", source: "gift" }))).toMatchObject({ kind: "validation" });
  });

  it("check-in once, then 409", async () => {
    expect((await A.submitCheckin({ planId: "m1_l1", cameUp: "yes", outcome: "didnt_help" })).outcome).toBe("didnt_help");
    expect(await failure(A.submitCheckin({ planId: "m1_l1", cameUp: "yes" }))).toEqual({ kind: "conflict", code: "checkin_already_answered" });
  });

  it("skills: fresh, then after a role-play run", async () => {
    expect((await A.getSkills()).counts.phrasesSaved).toBe(0);
    const start = await A.startRoleplay("m1_l1", "lesson");
    await A.finishRoleplay(start.runId, []);
    expect((await A.getSkills()).skills.some((s) => s.roleplay !== null)).toBe(true);
  });

  it("profile and visit sheet: empty, saved, and a rejected unknown key", async () => {
    expect((await A.getProfile()).displayName).toBeNull();
    expect((await A.putProfile({ displayName: "Margaret", rhythm: "Up at 7." })).displayName).toBe("Margaret");
    expect((await A.getProfile()).rhythm).toBe("Up at 7.");
    expect(await failure(A.putProfile({ diagnosis: "x" } as never))).toMatchObject({ kind: "validation" });
    expect((await A.getVisitSheet()).doctor).toBeNull();
    const saved = await A.putVisitSheet({ doctor: "Dr. Lee", questions: [{ text: "Is it OK?" }] });
    expect(saved.questions[0]).toMatchObject({ text: "Is it OK?", custom: true });
    expect(await failure(A.putVisitSheet({ questions: [{ id: "nope" }] }))).toMatchObject({ kind: "validation" });
  });

  it("care card: not_published, published, update_available, revoked, and 409s", async () => {
    expect((await A.getCareCard()).status).toBe("not_published");
    expect(await failure(A.updateCareCard([]))).toEqual({ kind: "conflict", code: "card_not_published" });
    expect((await A.publishCareCard([])).status).toBe("published");
    expect(await failure(A.publishCareCard([]))).toEqual({ kind: "conflict", code: "card_already_published" });
    await A.putProfile({ rhythm: "Changed." });
    expect((await A.getCareCard()).status).toBe("update_available");
    expect((await A.updateCareCard([])).status).toBe("published");
    expect((await A.revokeCareCard()).status).toBe("revoked");
  });

  it("public card: no token needed; 404, 410, 429 by scenario", async () => {
    clearToken();
    expect((await A.getPublicCard("REDACTED_CARD_ID")).displayName).toBeTruthy();
    expect(api.calls.at(-1)?.token).toBeNull();
    api.scenario.publicCard = "revoked";
    expect(await failure(A.getPublicCard("x"))).toEqual({ kind: "gone" });
    api.scenario.publicCard = "missing";
    expect(await failure(A.getPublicCard("x"))).toEqual({ kind: "not_found" });
    api.scenario.publicCard = "rate_limited";
    expect(await failure(A.getPublicCard("x"))).toEqual({ kind: "rate_limited" });
  });

  it("subscription, cancel preview and cancel (second cancel is 409)", async () => {
    expect((await A.getSubscription()).status).toBe("demo");
    expect((await A.getCancelPreview()).planName).toBeTruthy();
    expect((await A.cancelSubscription()).status).toBe("canceling");
    expect((await A.getSubscription()).status).toBe("canceling");
    expect(await failure(A.cancelSubscription())).toMatchObject({ kind: "conflict" });
    api.scenario.subscription = "active";
    expect((await A.getSubscription()).source).toBe("stripe");
  });

  it("503 billing_cancel_failed blocks both cancel and gentle exit, and nothing changes", async () => {
    api.scenario.cancelFails = true;
    expect(await failure(A.cancelSubscription())).toEqual({ kind: "billing_failed" });
    expect(await failure(A.gentleExit())).toEqual({ kind: "billing_failed" });
    expect((await A.getToday()).title).toBeTruthy(); // the session still exists
  });

  it("gentle exit and clear data end the session (401 afterwards)", async () => {
    expect((await A.gentleExit()).resources.length).toBeGreaterThan(0);
    expect(await failure(A.getToday())).toEqual({ kind: "session_lost" });
    setToken(signIn(api, "second"));
    expect((await A.clearMyData()).message).toBeTruthy();
    expect(await failure(A.getToday())).toEqual({ kind: "session_lost" });
  });

  it("402 past_due on every gated endpoint, but not on the ungated ones", async () => {
    api.scenario.subscription = "past_due";
    const gated = [
      () => A.getToday(), () => A.getLesson("m1_l1"), () => A.listPhrases(), () => A.getSkills(),
      () => A.getProfile(), () => A.getCareCard(), () => A.getVisitSheet(),
      () => A.startRoleplay("m1_l1", "lesson"),
    ];
    for (const run of gated) expect(await failure(run())).toEqual({ kind: "gate", reason: "past_due" });
    expect((await A.getAppCopy()).nav.today).toBe("Today");
    expect((await A.getSubscription()).status).toBe("past_due");
    expect((await A.getCancelPreview()).planName).toBeTruthy();
    await expect(A.getDemo()).resolves.toBeTruthy();
  });

  it("402 reasons by session state and by accessReason", async () => {
    api.sessions.set("noplan", { answers: {}, lastQuestionId: null, completed: false, subscribed: false, app: {} });
    setToken("noplan");
    expect(await failure(A.getToday())).toEqual({ kind: "gate", reason: "no_plan" });
    api.sessions.set("nosub", { answers: {}, lastQuestionId: null, completed: true, subscribed: false, app: {} });
    setToken("nosub");
    expect(await failure(A.getToday())).toEqual({ kind: "gate", reason: "no_subscription" });
    setToken(signIn(api, "ok"));
    api.scenario.accessReason = "ended";
    expect(await failure(A.getSkills())).toEqual({ kind: "gate", reason: "ended" });
  });

  it("401 for an unknown token; app-copy 500 by scenario", async () => {
    setToken("nobody");
    expect(await failure(A.getToday())).toEqual({ kind: "session_lost" });
    setToken(signIn(api, "x2"));
    api.scenario.appCopy = "error";
    expect(await failure(A.getAppCopy())).toEqual({ kind: "server" });
  });
});

describe("registry", () => {
  const area = "g1-test-area";
  afterEach(() => unregisterFakeArea(area));

  it("an area can add its own endpoint without touching the funnel fake", async () => {
    const routes: FakeRoute[] = [route("GET", "/skills", () => ({ status: 200, body: { mine: true } }))];
    registerFakeArea(area, routes);
    expect(await A.getSkills()).toEqual({ mine: true });
  });

  it("an area cannot bypass the gate", async () => {
    registerFakeArea(area, [route("GET", "/skills", () => ({ status: 200, body: { mine: true } }))]);
    api.scenario.subscription = "past_due";
    expect(await failure(A.getSkills())).toEqual({ kind: "gate", reason: "past_due" });
  });

  it("unknown paths are 404 and fixture access is by name", async () => {
    expect(await failure(A.getAppCopy().then(() => apiGetMissing()))).toEqual({ kind: "not_found" });
    expect(() => appFixture("nope")).toThrow(/No app fixture/);
  });
});

async function apiGetMissing(): Promise<unknown> {
  const { apiRequest } = await import("../../api/client");
  return apiRequest({ method: "GET", path: "/does-not-exist", auth: true });
}
