import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as A from "./app";
import { REQUEST_TIMEOUT_MS, apiRequest } from "./client";
import { classifyAppError, classifyError, gateRoute, isShellFailure } from "./errors";
import { clearToken, setToken } from "./session";
import { appFixture } from "../test/fakeApp/fixtures";

const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const errorBody = (code: string, details: unknown = {}): unknown => ({
  error: { code, message: "Server says no.", details },
});

const fetchMock = vi.fn<typeof fetch>();

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
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  const storage = memoryStorage();
  Object.defineProperty(window, "localStorage", { value: storage, configurable: true });
  clearToken();
  setToken("tok-1");
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const lastCall = (): { url: string; init: RequestInit; headers: Headers } => {
  const [url, init] = fetchMock.mock.calls.at(-1) ?? [];
  return { url: String(url), init: init ?? {}, headers: new Headers(init?.headers) };
};

describe("apiRequest additions (timeoutMs, 204)", () => {
  it("resolves undefined on 204 and on an empty body", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(apiRequest({ method: "DELETE", path: "/phrases/1", auth: true })).resolves.toBeUndefined();
    fetchMock.mockResolvedValueOnce(new Response("", { status: 200 }));
    await expect(apiRequest({ method: "GET", path: "/x", auth: true })).resolves.toBeUndefined();
  });

  it("keeps the 10 s default and honours timeoutMs", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("a", "AbortError")));
        }),
    );
    const slow = apiRequest({ method: "GET", path: "/x", auth: true, timeoutMs: 15_000 }).catch(
      (e: unknown) => e,
    );
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS + 1000);
    let settled = false;
    void slow.then(() => (settled = true));
    await vi.advanceTimersByTimeAsync(0);
    expect(settled).toBe(false); // still waiting at 11 s
    await vi.advanceTimersByTimeAsync(5000);
    expect(await slow).toMatchObject({ code: "timeout" });
    const dflt = apiRequest({ method: "GET", path: "/y", auth: true }).catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);
    expect(await dflt).toMatchObject({ code: "timeout" });
  });

  it("submitTurn waits up to 15 s, so the server's own fallback is not thrown away", async () => {
    expect(A.TURN_TIMEOUT_MS).toBe(15_000);
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url, init) =>
        new Promise<Response>((resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("a", "AbortError")));
          setTimeout(() => resolve(json(appFixture("roleplay-turn-fallback-1"))), 12_500);
        }),
    );
    const promise = A.submitTurn("run-1", { round: 1, reply: "hi there", previousTurns: [] });
    await vi.advanceTimersByTimeAsync(12_600);
    await expect(promise).resolves.toMatchObject({ mode: "fallback" });
  });
});

describe("one typed function per endpoint: method, path, body, token", () => {
  const cases: [string, () => Promise<unknown>, string, string, unknown?][] = [
    ["getAppCopy", () => A.getAppCopy(), "GET", "/api/app-copy"],
    ["getToday", () => A.getToday(), "GET", "/api/today"],
    ["getPlan", () => A.getPlan(), "GET", "/api/plan"],
    ["answerLesson", () => A.answerLesson("m1_l1", { screenId: "s1", value: "phone" }), "POST", "/api/lessons/m1_l1/answers", { screenId: "s1", value: "phone" }],
    ["completeLesson", () => A.completeLesson("m1_l1"), "POST", "/api/lessons/m1_l1/complete"],
    ["putLessonProgress", () => A.putLessonProgress("m1_l1", 3), "PUT", "/api/lessons/m1_l1/progress", { step: 3 }],
    ["startRoleplay", () => A.startRoleplay("m1_l1", "practice_round"), "POST", "/api/roleplay/start", { lessonId: "m1_l1", context: "practice_round" }],
    ["submitTurn", () => A.submitTurn("r 1", { round: 2, reply: "I'm here", previousTurns: [] }), "POST", "/api/roleplay/r%201/turn", { round: 2, reply: "I'm here", previousTurns: [] }],
    ["finishRoleplay", () => A.finishRoleplay("r1", [{ reply: "a", betterPhrase: "b" }]), "POST", "/api/roleplay/r1/finish", { phrases: [{ reply: "a", betterPhrase: "b" }] }],
    ["listPhrases", () => A.listPhrases(), "GET", "/api/phrases"],
    ["savePhrase", () => A.savePhrase({ text: "Hi", source: "gift" }), "POST", "/api/phrases", { text: "Hi", source: "gift" }],
    ["deletePhrase", () => A.deletePhrase("p1"), "DELETE", "/api/phrases/p1"],
    ["submitCheckin", () => A.submitCheckin({ planId: "m1_l1", cameUp: "yes" }), "POST", "/api/checkins", { planId: "m1_l1", cameUp: "yes" }],
    ["getSkills", () => A.getSkills(), "GET", "/api/skills"],
    ["getProfile", () => A.getProfile(), "GET", "/api/profile"],
    ["putProfile", () => A.putProfile({ rhythm: "Up at 7." }), "PUT", "/api/profile", { rhythm: "Up at 7." }],
    ["getCareCard", () => A.getCareCard(), "GET", "/api/care-card"],
    ["publishCareCard", () => A.publishCareCard(["p1"]), "POST", "/api/care-card", { phraseIds: ["p1"] }],
    ["updateCareCard", () => A.updateCareCard(["p1"]), "PUT", "/api/care-card", { phraseIds: ["p1"] }],
    ["revokeCareCard", () => A.revokeCareCard(), "DELETE", "/api/care-card"],
    ["getVisitSheet", () => A.getVisitSheet(), "GET", "/api/visit-sheet"],
    ["putVisitSheet", () => A.putVisitSheet({ doctor: "Dr. Lee" }), "PUT", "/api/visit-sheet", { doctor: "Dr. Lee" }],
    ["getSubscription", () => A.getSubscription(), "GET", "/api/billing/subscription"],
    ["getCancelPreview", () => A.getCancelPreview(), "GET", "/api/billing/cancel-preview"],
    ["cancelSubscription", () => A.cancelSubscription(), "POST", "/api/billing/cancel"],
    ["gentleExit", () => A.gentleExit(), "POST", "/api/exit/gentle"],
    ["clearMyData", () => A.clearMyData(), "DELETE", "/api/session"],
    ["getDemo", () => A.getDemo(), "GET", "/api/demo"],
    ["demoNextDay", () => A.demoNextDay(), "POST", "/api/demo/next-day"],
    ["demoJumpToRenewal", () => A.demoJumpToRenewal(), "POST", "/api/demo/jump-to-renewal"],
    ["demoFailNextPayment", () => A.demoFailNextPayment(), "POST", "/api/demo/fail-next-payment"],
  ];

  it.each(cases)("%s", async (_name, run, method, url, body) => {
    fetchMock.mockImplementation(() => Promise.resolve(json({ ok: true })));
    await run();
    const call = lastCall();
    expect(call.url).toBe(url);
    expect(call.init.method).toBe(method);
    expect(call.headers.get("X-Session-Token")).toBe("tok-1");
    if (body === undefined) expect(call.init.body).toBeUndefined();
    else expect(JSON.parse(String(call.init.body))).toEqual(body);
  });

  it("deletePhrase resolves undefined on 204", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(A.deletePhrase("p1")).resolves.toBeUndefined();
  });

  it("getPublicCard sends no token, and a 401 there cannot clear the stored token", async () => {
    fetchMock.mockResolvedValue(json(errorBody("invalid_session_token"), 401));
    await expect(A.getPublicCard("abc/def")).rejects.toMatchObject({ status: 401 });
    const call = lastCall();
    expect(call.url).toBe("/api/cards/abc%2Fdef");
    expect(call.headers.get("X-Session-Token")).toBeNull();
    clearToken();
    setToken("tok-2");
    fetchMock.mockResolvedValue(json(errorBody("invalid_session_token"), 401));
    await A.getPublicCard("x").catch(() => undefined);
    expect(window.localStorage.getItem("pcn_session_token")).toBe("tok-2");
  });

  it("getLesson maps an unknown screen type to a typed unknown screen", async () => {
    const lesson = appFixture<{ screens: unknown[] }>("lesson-m1_l2");
    lesson.screens.push({ id: "z9", type: "hologram" });
    fetchMock.mockResolvedValue(json(lesson));
    const got = await A.getLesson("m1_l2");
    expect(got.screens.at(-1)).toEqual({ id: "z9", type: "unknown" });
    expect(got.screens.slice(0, -1).every((s) => s.type !== "unknown")).toBe(true);
  });

  it("getLesson rejects a response without screens as an unexpected shape", async () => {
    fetchMock.mockResolvedValue(json({ id: "m1_l1" }));
    await expect(A.getLesson("m1_l1")).rejects.toMatchObject({ code: "invalid_response" });
  });
});

describe("failure kinds for the app", () => {
  const make = (status: number, code: string, details: unknown = {}): unknown => {
    fetchMock.mockResolvedValue(json(errorBody(code, details), status));
    return A.getToday().catch((e: unknown) => e);
  };

  it("401 clears the token; 402 carries each reason; the shell kinds are flagged", async () => {
    const lost = classifyAppError(await make(401, "invalid_session_token"));
    expect(lost).toEqual({ kind: "session_lost" });
    expect(isShellFailure(lost)).toBe(true);
    expect(window.localStorage.getItem("pcn_session_token")).toBeNull();
    for (const reason of ["no_plan", "no_subscription", "past_due", "ended"] as const) {
      const failure = classifyAppError(await make(402, "payment_required", { reason }));
      expect(failure).toEqual({ kind: "gate", reason });
      expect(isShellFailure(failure)).toBe(true);
    }
  });

  it("past_due stays in the app (today), never the paywall", () => {
    expect(gateRoute("past_due")).toEqual({ path: "/today", notice: "past_due" });
  });

  it("423 carries unlockOn; 404, 410, 409, 503, 429, 5xx and network map to kinds", async () => {
    expect(classifyAppError(await make(423, "lesson_locked", { unlockOn: "2026-01-07" }))).toEqual({
      kind: "lesson_locked",
      unlockOn: "2026-01-07",
    });
    expect(classifyAppError(await make(423, "lesson_locked"))).toEqual({ kind: "lesson_locked", unlockOn: null });
    expect(classifyAppError(await make(404, "card_not_found"))).toEqual({ kind: "not_found" });
    expect(classifyAppError(await make(410, "card_revoked"))).toEqual({ kind: "gone" });
    expect(classifyAppError(await make(409, "invalid_transition"))).toEqual({ kind: "conflict", code: "invalid_transition" });
    expect(classifyAppError(await make(503, "billing_cancel_failed"))).toEqual({ kind: "billing_failed" });
    expect(classifyAppError(await make(429, "rate_limited"))).toEqual({ kind: "rate_limited" });
    expect(classifyAppError(await make(500, "boom"))).toEqual({ kind: "server" });
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    expect(classifyAppError(await A.getToday().catch((e: unknown) => e))).toEqual({ kind: "network" });
  });

  it("funnel classification is unchanged for the funnel kinds", async () => {
    expect(classifyError(await make(409, "quiz_locked"))).toEqual({ kind: "locked", code: "quiz_locked" });
    expect(classifyAppError(await make(409, "quiz_locked"))).toEqual({ kind: "locked", code: "quiz_locked" });
  });

  it("request and response bodies never reach the console", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((m) =>
      vi.spyOn(console, m).mockImplementation(() => undefined),
    );
    fetchMock.mockResolvedValueOnce(json(errorBody("invalid_reply"), 422));
    await A.submitTurn("r1", { round: 1, reply: "private words", previousTurns: [] }).catch(() => undefined);
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await A.putProfile({ rhythm: "private rhythm" }).catch(() => undefined);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
  });

  it("the reply text is only in the request body, never in the URL", async () => {
    fetchMock.mockResolvedValue(json(appFixture("roleplay-turn-ai-1")));
    await A.submitTurn("r1", { round: 1, reply: "secret-words-xyz", previousTurns: [] });
    expect(lastCall().url).not.toContain("secret-words-xyz");
  });
});
