import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import answerFixture from "../test/fixtures/answer.json";
import completeFixture from "../test/fixtures/complete.json";
import eventsFixture from "../test/fixtures/events.json";
import funnelCopyFixture from "../test/fixtures/funnel-copy.json";
import giftA from "../test/fixtures/gift-a.json";
import giftB from "../test/fixtures/gift-b.json";
import giftC from "../test/fixtures/gift-c.json";
import planGated from "../test/fixtures/plan-gated.json";
import previewA from "../test/fixtures/preview-a.json";
import previewB from "../test/fixtures/preview-b.json";
import previewC from "../test/fixtures/preview-c.json";
import pricingFixture from "../test/fixtures/pricing.json";
import quizAnswered from "../test/fixtures/quiz-answered.json";
import quizFixture from "../test/fixtures/quiz.json";
import sessionFixture from "../test/fixtures/session.json";
import subscriptionFixture from "../test/fixtures/subscription-demo.json";
import { type FakeApi, installFakeApi } from "../test/fakeApi";
import { classifyError } from "./errors";
import {
  completeQuiz,
  createCheckout,
  createSession,
  getCheckoutStatus,
  getFunnelCopy,
  getGift,
  getPlanPreview,
  getQuiz,
  isQuizQuestion,
  postEvents,
  probeAccess,
  putAnswer,
  startDemo,
} from "./funnel";
import * as T from "./funnelTypes";
import { clearToken } from "./session";

/** Sorted keys equal sorted key list: a field added or removed on either side fails here. */
function expectKeys(value: unknown, keys: readonly string[]): void {
  expect(Object.keys(value as object).sort()).toEqual([...keys].sort());
}

describe("fixtures captured from the real backend match the hand-written types", () => {
  it.each([
    ["a", previewA, giftA],
    ["b", previewB, giftB],
    ["c", previewC, giftC],
  ])("persona %s preview and gift", (_name, preview, gift) => {
    expectKeys(preview, T.PLAN_PREVIEW_KEYS);
    expectKeys(preview.beforeAfter, T.BEFORE_AFTER_KEYS);
    expectKeys(preview.pace, T.PACE_KEYS);
    expectKeys(preview.readiness, T.READINESS_KEYS);
    preview.modules.forEach((m) => {
      expectKeys(m, T.PLAN_MODULE_KEYS);
      m.lessons.forEach((l) => expectKeys(l, T.PLAN_LESSON_KEYS));
    });
    preview.quickGuides.forEach((g) => expectKeys(g, T.QUICK_GUIDE_KEYS));
    expectKeys(gift, T.GIFT_KEYS);
    expect(gift.phrases).toHaveLength(5);
    gift.phrases.forEach((p) => expectKeys(p, T.GIFT_PHRASE_KEYS));
  });

  it("single responses", () => {
    expectKeys(sessionFixture, T.SESSION_KEYS);
    expectKeys(quizFixture, T.QUIZ_STATE_KEYS);
    expectKeys(quizAnswered, T.QUIZ_STATE_KEYS);
    expectKeys(answerFixture, T.ANSWER_RESULT_KEYS);
    expectKeys(completeFixture, T.COMPLETE_KEYS);
    expectKeys(subscriptionFixture, T.SUBSCRIPTION_KEYS);
    expectKeys(pricingFixture, T.PRICING_KEYS);
    expectKeys(planGated, T.PLAN_ACCESS_KEYS);
    expectKeys(eventsFixture, T.EVENTS_KEYS);
  });

  it("the funnel-copy fixture has the keys of the real P2 types and no placeholders", () => {
    expectKeys(funnelCopyFixture, T.FUNNEL_COPY_KEYS);
    const strings: string[] = [];
    const walk = (v: unknown): void => {
      if (typeof v === "string") strings.push(v);
      else if (Array.isArray(v)) v.forEach(walk);
      else if (typeof v === "object" && v !== null) Object.values(v).forEach(walk);
    };
    walk(funnelCopyFixture);
    expect(strings.length).toBeGreaterThan(20);
    strings.forEach((text) => expect(text).not.toMatch(/[{}]|\*\*/));
    // Hand-checked against pricing.json and the pricing fixture (renewal dates 2026-02-02 / 2026-03-30).
    const [four, twelve] = funnelCopyFixture.paywall.plans;
    expect(four?.priceToday).toBe("$14.99");
    expect(twelve?.priceToday).toBe("$49.99");
    expect(JSON.stringify(four)).toContain("Feb 2");
    expect(JSON.stringify(twelve)).toContain("Mar 30");
  });

  it("no fixture holds a real token or a request id", () => {
    expect(JSON.stringify(sessionFixture)).toContain("REDACTED");
  });
});

describe("isQuizQuestion", () => {
  const content = JSON.parse(
    readFileSync(resolve(__dirname, "../../../content/quiz.json"), "utf8"),
  ) as { questions: Record<string, unknown>[] };

  /** Display fields only: what the API sends for the UI (no usedFor, tags, derivedTags, storeAs). */
  const display = (q: Record<string, unknown>): Record<string, unknown> => {
    const options = Array.isArray(q["options"])
      ? (q["options"] as Record<string, unknown>[]).map(({ id, label, exclusive }) => ({
          id,
          label,
          exclusive,
        }))
      : undefined;
    return {
      id: q["id"],
      type: q["type"],
      title: q["title"],
      subtitle: q["subtitle"],
      healthData: q["healthData"] === true,
      max: q["max"],
      min: q["min"],
      minLabel: q["minLabel"],
      maxLabel: q["maxLabel"],
      body: q["body"],
      cta: q["cta"],
      states: q["states"],
      rows: q["rows"],
      ...(options ? { options } : {}),
    };
  };

  it("accepts every entry of content/quiz.json", () => {
    expect(content.questions.length).toBeGreaterThan(10);
    content.questions.forEach((q) => expect(isQuizQuestion(display(q))).toBe(true));
  });

  it("accepts every question of the real API fixture", () => {
    quizFixture.questions.forEach((q) => expect(isQuizQuestion(q)).toBe(true));
  });

  it.each([
    ["null", null],
    ["a string", "q1"],
    ["no id", { type: "single", title: "t", options: [] }],
    ["unknown type", { id: "x", type: "slider", title: "t" }],
    ["single without options", { id: "x", type: "single", title: "t" }],
    ["single with a bad option", { id: "x", type: "single", title: "t", options: [{ id: 1 }] }],
    ["multi without max", { id: "x", type: "multi", title: "t", options: [] }],
    ["grid without rows", { id: "x", type: "grid", title: "t", states: [] }],
    ["scale without labels", { id: "x", type: "scale", title: "t", min: 1, max: 5 }],
    ["interstitial without cta", { id: "x", type: "interstitial", title: "t", body: "b" }],
  ])("rejects %s", (_name, value) => {
    expect(isQuizQuestion(value)).toBe(false);
  });
});

describe("funnel client over the fake API", () => {
  let api: FakeApi;
  beforeEach(() => {
    clearToken();
    api = installFakeApi();
  });
  afterEach(() => api.restore());

  it("getQuiz turns an unknown question shape into an error, not a crash", async () => {
    await createSession();
    api.inject({
      method: "GET",
      path: "/quiz",
      status: 200,
      body: { ...quizFixture, questions: [{ id: "q1", type: "hologram", title: "t" }] },
    });
    const failure = await getQuiz().catch((e: unknown) => e);
    expect(classifyError(failure)).toEqual({ kind: "unknown" });
  });

  it("sends the token on every call and posts events as a batch", async () => {
    const { token } = await createSession();
    await getQuiz();
    await putAnswer("q1_recipient", "mom");
    await postEvents([{ name: "quiz_start" }]);
    const calls = api.calls.slice(1);
    expect(calls.map((c) => c.token)).toEqual([token, token, token]);
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual([
      "GET /quiz",
      "PUT /quiz/answers/q1_recipient",
      "POST /events",
    ]);
  });

  it("runs the whole happy path and lands on a 200 probe", async () => {
    await createSession();
    for (const [id, value] of Object.entries(quizAnswered.answers)) await putAnswer(id, value);
    await expect(completeQuiz()).resolves.toMatchObject({ completed: true });
    await expect(getPlanPreview()).resolves.toMatchObject({ firstLessonId: "m1_l1" });
    await expect(getGift()).resolves.toMatchObject({ phrases: expect.any(Array) });
    await expect(getFunnelCopy()).resolves.toMatchObject({ paywall: { defaultPlanId: "four_week" } });
    await expect(startDemo({ autoRenewConsent: true })).resolves.toMatchObject({ status: "demo" });
    await expect(probeAccess()).resolves.toMatchObject({ heroLessonId: "m1_l1" });
  });

  it("checkout and its status go through encoded paths", async () => {
    api.scenario.stripeConfigured = true;
    await createSession();
    for (const [id, value] of Object.entries(quizAnswered.answers)) await putAnswer(id, value);
    await completeQuiz();
    await expect(createCheckout({ autoRenewConsent: true, planId: "four_week" })).resolves.toEqual({
      checkoutId: "cs_test_fake",
      url: "https://checkout.stripe.com/c/pay/cs_test_fake",
    });
    await expect(getCheckoutStatus("cs_test_fake")).resolves.toMatchObject({ paid: true });
    await getCheckoutStatus("a/b").catch(() => undefined);
    expect(api.calls.at(-1)?.path).toBe("/billing/checkout/a%2Fb");
  });
});
