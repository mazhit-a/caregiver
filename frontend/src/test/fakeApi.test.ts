import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { classifyError } from "../api/errors";
import {
  completeQuiz,
  createCheckout,
  createSession,
  getFunnelCopy,
  getGift,
  getPlanPreview,
  getPricing,
  getQuiz,
  postEvents,
  probeAccess,
  putAnswer,
  startDemo,
} from "../api/funnel";
import { clearToken, setToken } from "../api/session";
import { type FakeApi, type Persona, installFakeApi } from "./fakeApi";
import fixtureQuiz from "./fixtures/quiz.json";

const PERSONA_ANSWERS: Record<Persona, Record<string, unknown>> = {
  a: {
    q1_recipient: "dad", q2_age: "65_74", q3_situation: "noticing", q6_living: "nearby",
    q7_helpers: "siblings", q8_work: "part_time", q9_worries: ["future"],
    q10_documents: { healthcare_proxy: "have", financial_poa: "have", hipaa_release: "have" },
    q11_confidence: 3, q12_time: "5",
  },
  b: {
    q1_recipient: "mom", q2_age: "75_84", q3_situation: "recent", q5_changes: ["repeats", "evenings"],
    q6_living: "far", q7_helpers: "just_me", q8_work: "full_time", q9_worries: ["what_to_say", "legal_money"],
    q10_documents: { healthcare_proxy: "missing", financial_poa: "not_sure", hipaa_release: "have" },
    q11_confidence: 2, q12_time: "10",
  },
  c: {
    q1_recipient: "mom", q2_age: "85plus", q3_situation: "hospital", q5_changes: ["refuses", "lost"],
    q6_living: "with_me", q7_helpers: "paid", q8_work: "not_now", q9_worries: ["safety", "me"],
    q10_documents: { healthcare_proxy: "missing", financial_poa: "missing", hipaa_release: "missing" },
    q11_confidence: 4, q12_time: "15",
  },
};

async function answerAll(persona: Persona): Promise<void> {
  for (const [id, value] of Object.entries(PERSONA_ANSWERS[persona])) {
    await putAnswer(id, value as never);
  }
}

const failureOf = async (p: Promise<unknown>): Promise<ReturnType<typeof classifyError>> =>
  classifyError(await p.then(() => undefined, (e: unknown) => e));

let api: FakeApi;
beforeEach(() => {
  clearToken();
  api = installFakeApi();
});
afterEach(() => api.restore());

describe("fake API contract", () => {
  it("401 for a missing or unknown token on session-only endpoints", async () => {
    expect(await failureOf(getQuiz())).toEqual({ kind: "session_lost" });
    setToken("nope");
    expect(await failureOf(getQuiz())).toEqual({ kind: "session_lost" });
    expect(await failureOf(postEvents([{ name: "quiz_start" }]))).toEqual({ kind: "session_lost" });
    expect(await failureOf(getFunnelCopy())).toEqual({ kind: "session_lost" });
  });

  it("pricing is public, and carries renewal dates only with a session", async () => {
    expect((await getPricing()).plans[0]?.firstRenewalDate).toBeNull();
    await createSession();
    expect((await getPricing()).plans[0]?.firstRenewalDate).toBe("2026-02-02");
  });

  it("serves the quiz and stores answers per session", async () => {
    await createSession();
    const empty = await getQuiz();
    expect(empty.questions).toHaveLength(fixtureQuiz.questions.length);
    expect(empty).toMatchObject({ answers: {}, completed: false, locked: false, branch: null });
    await putAnswer("q1_recipient", "mom");
    await putAnswer("q3_situation", "recent");
    expect(await getQuiz()).toMatchObject({
      answers: { q1_recipient: "mom", q3_situation: "recent" },
      branch: "recent",
      lastQuestionId: "q3_situation",
    });
  });

  it("422 invalid_answer for an unknown question and for an interstitial", async () => {
    await createSession();
    const unknown = await failureOf(putAnswer("q99", "x"));
    expect(unknown).toMatchObject({ kind: "validation", code: "invalid_answer" });
    expect(await failureOf(putAnswer("reassure_1", "x"))).toMatchObject({ code: "invalid_answer" });
  });

  it("422 quiz_incomplete lists the missing ids; q5 is skippable", async () => {
    await createSession();
    const failure = await failureOf(completeQuiz());
    expect(failure).toMatchObject({ kind: "validation", code: "quiz_incomplete" });
    if (failure.kind === "validation") {
      expect((failure.details as { questionIds: string[] }).questionIds).not.toContain("q5_changes");
      expect((failure.details as { questionIds: string[] }).questionIds).toContain("q1_recipient");
    }
    await answerAll("a"); // persona A skips q5
    await expect(completeQuiz()).resolves.toMatchObject({ completed: true });
  });

  it("402 no_plan before complete; preview and gift follow the persona after", async () => {
    await createSession();
    expect(await failureOf(getPlanPreview())).toEqual({ kind: "gate", reason: "no_plan" });
    expect(await failureOf(getGift())).toEqual({ kind: "gate", reason: "no_plan" });
    await answerAll("c");
    await completeQuiz();
    expect((await getPlanPreview()).whatWeHeard[0]).toBe("Mom just came home from the hospital.");
    expect((await getGift()).phrases).toHaveLength(5);
  });

  it("gate probe: no_plan, then no_subscription, then 200", async () => {
    await createSession();
    expect(await failureOf(probeAccess())).toEqual({ kind: "gate", reason: "no_plan" });
    await answerAll("b");
    await completeQuiz();
    expect(await failureOf(probeAccess())).toEqual({ kind: "gate", reason: "no_subscription" });
    await startDemo({ autoRenewConsent: true });
    await expect(probeAccess()).resolves.toMatchObject({ lessonsPerWeek: expect.any(Number) });
  });

  it("scenario accessReason serves past_due and ended through the probe", async () => {
    await createSession();
    await answerAll("b");
    await completeQuiz();
    await startDemo({ autoRenewConsent: true });
    api.scenario.accessReason = "past_due";
    expect(await failureOf(probeAccess())).toEqual({ kind: "gate", reason: "past_due" });
    api.scenario.accessReason = "ended";
    expect(await failureOf(probeAccess())).toEqual({ kind: "gate", reason: "ended" });
  });

  it("demo needs consent (422), a plan (402), and locks the quiz after (409)", async () => {
    await createSession();
    expect(await failureOf(startDemo({ autoRenewConsent: true }))).toEqual({
      kind: "gate",
      reason: "no_plan",
    });
    await answerAll("a");
    await completeQuiz();
    expect(await failureOf(startDemo({ autoRenewConsent: false }))).toMatchObject({
      kind: "validation",
      code: "consent_required",
    });
    await expect(startDemo({ autoRenewConsent: true })).resolves.toMatchObject({ status: "demo" });
    expect(await failureOf(startDemo({ autoRenewConsent: true }))).toEqual({
      kind: "locked",
      code: "already_subscribed",
    });
    expect(await failureOf(putAnswer("q1_recipient", "mom"))).toEqual({
      kind: "locked",
      code: "quiz_locked",
    });
    expect(await failureOf(completeQuiz())).toEqual({ kind: "locked", code: "quiz_locked" });
    expect((await getQuiz()).locked).toBe(true);
  });

  it("checkout is 502 with the demo hint unless Stripe is configured", async () => {
    await createSession();
    expect(await failureOf(createCheckout({ autoRenewConsent: true }))).toEqual({
      kind: "gateway",
      demoHint: true,
    });
    api.scenario.stripeConfigured = true;
    await expect(createCheckout({ autoRenewConsent: true })).resolves.toMatchObject({
      url: expect.stringMatching(/^https:\/\/checkout\.stripe\.com\//) as string,
    });
    expect(await failureOf(createCheckout({ autoRenewConsent: false }))).toMatchObject({
      code: "consent_required",
    });
  });

  it("429 on demand for session creation and events", async () => {
    api.scenario.sessionRateLimited = true;
    expect(await failureOf(createSession())).toEqual({ kind: "rate_limited" });
    api.scenario.sessionRateLimited = false;
    await createSession();
    api.scenario.eventsRateLimited = true;
    expect(await failureOf(postEvents([{ name: "quiz_start" }]))).toEqual({ kind: "rate_limited" });
    api.scenario.eventsRateLimited = false;
    await expect(postEvents([{ name: "quiz_start" }, { name: "quiz_back" }])).resolves.toEqual({
      stored: 2,
    });
  });

  it("failure switches: inject once, then recover; network down", async () => {
    await createSession();
    api.injectError("GET", "/quiz", 500, "internal_error");
    expect(await failureOf(getQuiz())).toEqual({ kind: "server" });
    await expect(getQuiz()).resolves.toMatchObject({ completed: false });
    api.scenario.networkDown = true;
    expect(await failureOf(getQuiz())).toEqual({ kind: "network" });
  });
});
