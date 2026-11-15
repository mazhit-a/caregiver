/**
 * Registry of fake app endpoints. `installFakeApi` asks it for every path it does not serve
 * itself. Each area adds ONLY its own `src/test/fakeApp/<area>.ts` and calls `registerFakeArea`;
 * a later registration wins over an earlier one, so an area can refine what `core.ts` serves.
 */

export type RoleplayMode = "ai" | "medical" | "fallback" | "crisis" | "emergency";
export type TodayState = "fresh" | "after_lesson_1" | "day2" | "nudge" | "all_done";
export type SubscriptionState =
  | "demo"
  | "active"
  | "canceling"
  | "past_due"
  | "canceled"
  | "ended"
  | "none";
export type PublicCardState = "ok" | "revoked" | "missing" | "rate_limited";

/** Scenario switches of the app endpoints (merged into the fake's `FakeScenario`). */
export interface AppScenario {
  /** `GET /app-copy`: "error" answers 500. */
  appCopy: "ok" | "error";
  /** Status served by `/billing/subscription`; `past_due` also makes every gated endpoint answer 402. */
  subscription: SubscriptionState;
  /** Off: `/demo*` answer 404 and Today carries no demo block (like `DEMO_CONTROLS=false`). */
  demoControls: boolean;
  /** One entry is consumed per role-play turn; the last one repeats. A `fallback` run stays in fallback. */
  roleplayMode: RoleplayMode[];
  /** Which Today fixture is served. `next-day` moves `after_lesson_1` to `day2`. */
  today: TodayState;
  /** What `GET /cards/:id` answers. */
  publicCard: PublicCardState;
  /** `POST /billing/cancel` and `POST /exit/gentle` answer 503 `billing_cancel_failed` (nothing changes). */
  cancelFails: boolean;
  /** Serve lesson 1 as the 24-screen lesson (`lessonV2.ts`). Default off until the player moves to it (C5). */
  lesson24: boolean;
}

export const DEFAULT_APP_SCENARIO: AppScenario = {
  appCopy: "ok",
  subscription: "demo",
  demoControls: true,
  roleplayMode: ["ai"],
  today: "fresh",
  publicCard: "ok",
  cancelFails: false,
  lesson24: false,
};

/** Per-session scratch space of the app fakes (phrases, profile, role-play runs ...). */
export interface FakeAppSession {
  completed: boolean;
  subscribed: boolean;
  app: Record<string, unknown>;
  /** Forget this session: the next request with its token answers 401. */
  destroy: () => void;
}

export interface FakeReq {
  method: string;
  /** Path after `/api`, without the query string. */
  path: string;
  body: Record<string, unknown>;
  token: string | null;
  scenario: AppScenario & { accessReason: string | null };
  /** Undefined for public routes (no valid token). */
  session: FakeAppSession | undefined;
}

export interface FakeRes {
  status: number;
  /** Omitted for 204. */
  body?: unknown;
}

/** Returns a response, or undefined when the request is not this route's. */
export type FakeRoute = (req: FakeReq) => FakeRes | undefined;

const areas = new Map<string, FakeRoute[]>();

export function registerFakeArea(name: string, routes: FakeRoute[]): void {
  areas.delete(name); // re-registering moves the area to the front of the precedence order
  areas.set(name, routes);
}

export function unregisterFakeArea(name: string): void {
  areas.delete(name);
}

/** Latest registered area first. */
export function serveFakeAreas(req: FakeReq): FakeRes | undefined {
  for (const routes of [...areas.values()].reverse()) {
    for (const route of routes) {
      const res = route(req);
      if (res) return res;
    }
  }
  return undefined;
}

/** `route("GET", "/phrases", handler)` or with a regexp whose groups are passed to the handler. */
export function route(
  method: string,
  pattern: string | RegExp,
  handler: (req: FakeReq, params: string[]) => FakeRes,
): FakeRoute {
  return (req) => {
    if (req.method !== method) return undefined;
    if (typeof pattern === "string") return req.path === pattern ? handler(req, []) : undefined;
    const match = pattern.exec(req.path);
    return match ? handler(req, match.slice(1).map((g) => decodeURIComponent(g))) : undefined;
  };
}
