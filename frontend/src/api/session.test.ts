import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, REQUEST_TIMEOUT_MS, apiRequest } from "./client";
import { classifyError, gateRoute, missingQuestionIds } from "./errors";
import { TOKEN_KEY, clearToken, createSession, getToken, setToken } from "./session";

const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const errorBody = (code: string, details: unknown = {}): unknown => ({
  error: { code, message: "msg", details },
});

const fetchMock = vi.fn<typeof fetch>();

/** jsdom under newer Node can lack a working localStorage: give the tests a plain in-memory one. */
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
let storage = memoryStorage();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  storage = memoryStorage();
  vi.stubGlobal("localStorage", storage);
  Object.defineProperty(window, "localStorage", { value: storage, configurable: true });
  clearToken();
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("apiRequest", () => {
  it("sends the token header only when auth is true", async () => {
    setToken("tok-1");
    fetchMock.mockImplementation(() => Promise.resolve(json({ ok: 1 })));
    await apiRequest({ method: "GET", path: "/quiz", auth: true });
    await apiRequest({ method: "GET", path: "/pricing", auth: false });
    const withAuth = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
    const without = new Headers(fetchMock.mock.calls[1]?.[1]?.headers);
    expect(withAuth.get("X-Session-Token")).toBe("tok-1");
    expect(without.get("X-Session-Token")).toBeNull();
  });

  it("sends a JSON body with a content type, and none on a GET", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(json({})));
    await apiRequest({ method: "PUT", path: "/x", body: { value: "mom" }, auth: true });
    await apiRequest({ method: "GET", path: "/x", auth: true });
    const put = fetchMock.mock.calls[0]?.[1];
    expect(put?.method).toBe("PUT");
    expect(put?.body).toBe('{"value":"mom"}');
    expect(new Headers(put?.headers).get("Content-Type")).toBe("application/json");
    expect(fetchMock.mock.calls[1]?.[1]?.body).toBeUndefined();
  });

  it("never writes request bodies to the console", async () => {
    const spies = (["log", "info", "warn", "error", "debug"] as const).map((m) =>
      vi.spyOn(console, m).mockImplementation(() => undefined),
    );
    fetchMock.mockResolvedValueOnce(json(errorBody("quiz_locked"), 409));
    fetchMock.mockResolvedValueOnce(json({ ok: 1 }));
    await apiRequest({
      method: "PUT",
      path: "/quiz/answers/q3_situation",
      body: { value: "hospital-secret" },
      auth: true,
    }).catch(() => undefined);
    await apiRequest({ method: "POST", path: "/x", body: { value: "hospital-secret" }, auth: true });
    spies.forEach((spy) => expect(spy).not.toHaveBeenCalled());
  });

  it("clears the stored token on a 401", async () => {
    setToken("stale");
    fetchMock.mockResolvedValue(json(errorBody("invalid_session_token"), 401));
    await expect(apiRequest({ method: "GET", path: "/quiz", auth: true })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(getToken()).toBeNull();
  });

  it("keeps the token on other errors", async () => {
    setToken("keep");
    fetchMock.mockResolvedValue(json(errorBody("boom"), 500));
    await apiRequest({ method: "GET", path: "/x", auth: true }).catch(() => undefined);
    expect(getToken()).toBe("keep");
  });

  it("times out after the shared budget", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url, init) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(new DOMException("a", "AbortError")));
        }),
    );
    const result = apiRequest({ method: "GET", path: "/x", auth: true }).catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS + 1);
    expect(await result).toMatchObject({ code: "timeout" });
  });

  it("maps a dropped connection to network_error", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(apiRequest({ method: "GET", path: "/x", auth: false })).rejects.toMatchObject({
      status: 0,
      code: "network_error",
    });
  });
});

describe("classifyError", () => {
  const make = (status: number, code: string, details: unknown = {}): ApiError =>
    new ApiError(status, code, "m", details);

  it.each([
    [new ApiError(0, "network_error", "m"), { kind: "network" }],
    [new ApiError(0, "timeout", "m"), { kind: "timeout" }],
    [make(401, "invalid_session_token"), { kind: "session_lost" }],
    [make(429, "rate_limited"), { kind: "rate_limited" }],
    [make(402, "payment_required", { reason: "past_due" }), { kind: "gate", reason: "past_due" }],
    [make(409, "quiz_locked"), { kind: "locked", code: "quiz_locked" }],
    [make(409, "already_subscribed"), { kind: "locked", code: "already_subscribed" }],
    [make(422, "consent_required"), { kind: "validation", code: "consent_required", details: {} }],
    [make(502, "payment_gateway_error", { hint: "demo_mode" }), { kind: "gateway", demoHint: true }],
    [make(502, "payment_gateway_error"), { kind: "gateway", demoHint: false }],
    [make(500, "internal_error"), { kind: "server" }],
    [make(404, "not_found"), { kind: "unknown" }],
    [make(402, "payment_required", {}), { kind: "unknown" }],
    [new Error("x"), { kind: "unknown" }],
  ])("%#", (error, expected) => {
    expect(classifyError(error)).toEqual(expected);
  });

  it("carries the missing question ids of quiz_incomplete", () => {
    const failure = classifyError(make(422, "quiz_incomplete", { questionIds: ["q1_recipient", 3] }));
    expect(missingQuestionIds(failure)).toEqual(["q1_recipient"]);
    expect(missingQuestionIds({ kind: "server" })).toEqual([]);
  });
});

describe("gateRoute", () => {
  it("is the one reason-to-route table", () => {
    expect(gateRoute("no_plan")).toEqual({ path: "/quiz", notice: null });
    expect(gateRoute("no_subscription")).toEqual({ path: "/paywall", notice: null });
    expect(gateRoute("past_due")).toEqual({ path: "/paywall", notice: "past_due" });
    expect(gateRoute("ended")).toEqual({ path: "/", notice: null });
  });
});

describe("session token storage", () => {
  it("stores under pcn_session_token", () => {
    setToken("abc");
    expect(storage.getItem(TOKEN_KEY)).toBe("abc");
    expect(getToken()).toBe("abc");
    clearToken();
    expect(storage.getItem(TOKEN_KEY)).toBeNull();
    expect(getToken()).toBeNull();
  });

  it("falls back to memory when storage throws", () => {
    const blocked = (): never => {
      throw new Error("blocked");
    };
    Object.defineProperty(window, "localStorage", {
      value: { getItem: blocked, setItem: blocked, removeItem: blocked },
      configurable: true,
    });
    expect(() => setToken("mem")).not.toThrow();
    expect(getToken()).toBe("mem");
    expect(() => clearToken()).not.toThrow();
    expect(getToken()).toBeNull();
  });
});

describe("createSession", () => {
  it("is single-flight and stores the token", async () => {
    let resolve: (r: Response) => void = () => undefined;
    fetchMock.mockImplementation(() => new Promise<Response>((r) => (resolve = r)));
    const first = createSession();
    const second = createSession();
    expect(second).toBe(first);
    resolve(json({ token: "new-token", timezone: "UTC" }, 201));
    await expect(first).resolves.toEqual({ token: "new-token", timezone: "UTC" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(getToken()).toBe("new-token");
  });

  it("posts the browser timezone and no token", async () => {
    setToken("old");
    fetchMock.mockResolvedValue(json({ token: "t", timezone: "UTC" }, 201));
    await createSession();
    const init = fetchMock.mock.calls[0]?.[1];
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    expect(JSON.parse(String(init?.body))).toEqual({ timezone: zone });
    expect(new Headers(init?.headers).get("X-Session-Token")).toBeNull();
  });

  it("allows a new attempt after a failure and surfaces 429", async () => {
    fetchMock.mockResolvedValueOnce(json(errorBody("rate_limited"), 429));
    const failure = await createSession().catch((e: unknown) => e);
    expect(classifyError(failure)).toEqual({ kind: "rate_limited" });
    fetchMock.mockResolvedValueOnce(json({ token: "t2", timezone: "UTC" }, 201));
    await expect(createSession()).resolves.toMatchObject({ token: "t2" });
  });
});
