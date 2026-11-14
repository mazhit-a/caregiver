/**
 * Demo-control area of the fake API (G5). Session switches live in `session.app`:
 * `demoSyncPolls` (number): next-day answers `billingSync: "pending"`, and `GET /billing/subscription`
 * stays `pending` for that many polls, then `done` (Infinity: never).
 * `demoFail` (boolean): the demo POSTs answer 500.
 * `demoCalls` (number): how many demo POSTs were served.
 */
import { appFixture } from "./fixtures";
import { type FakeRes, registerFakeArea, route } from "./registry";

const ok = (body: unknown): FakeRes => ({ status: 200, body });

registerFakeArea("demo", [
  route("POST", /^\/demo\/(next-day|jump-to-renewal)$/, (req, [kind]) => {
    const app = req.session?.app ?? {};
    if (!req.scenario.demoControls) {
      return { status: 404, body: { error: { code: "not_found", message: "Not found.", details: {} } } };
    }
    app["demoCalls"] = ((app["demoCalls"] as number | undefined) ?? 0) + 1;
    if (app["demoFail"]) {
      return { status: 500, body: { error: { code: "internal_error", message: "Something went wrong.", details: {} } } };
    }
    if (kind === "next-day" && req.scenario.today === "after_lesson_1") req.scenario.today = "day2";
    const body = appFixture<Record<string, unknown>>(kind === "next-day" ? "demo-next-day" : "demo-jump-to-renewal");
    const polls = app["demoSyncPolls"] as number | undefined;
    return ok(polls === undefined ? body : { ...body, billingSync: "pending" });
  }),
  (req) => {
    if (req.method !== "GET" || req.path !== "/billing/subscription") return undefined;
    const app = req.session?.app;
    const polls = app?.["demoSyncPolls"] as number | undefined;
    if (!app || polls === undefined) return undefined;
    const seen = ((app["demoSyncSeen"] as number | undefined) ?? 0) + 1;
    app["demoSyncSeen"] = seen;
    const base = appFixture<Record<string, unknown>>("subscription-demo");
    return ok({ ...base, billingSync: seen > polls ? "done" : "pending" });
  },
]);
