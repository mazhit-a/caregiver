import { ROUTES } from "../routes";
import { ApiError } from "./client";

export type AccessReason = "no_plan" | "no_subscription" | "past_due" | "ended";

export type ApiFailure =
  | { kind: "network" }
  | { kind: "timeout" }
  | { kind: "session_lost" }
  | { kind: "rate_limited" }
  | { kind: "gate"; reason: AccessReason }
  | { kind: "locked"; code: "quiz_locked" | "already_subscribed" }
  | { kind: "validation"; code: string; details: unknown }
  | { kind: "gateway"; demoHint: boolean }
  | { kind: "server" }
  | { kind: "unknown" };

export type ApiFailureKind = ApiFailure["kind"];

const REASONS: readonly string[] = ["no_plan", "no_subscription", "past_due", "ended"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function gateReason(details: unknown): AccessReason | null {
  const reason = isRecord(details) ? details["reason"] : undefined;
  return typeof reason === "string" && REASONS.includes(reason) ? (reason as AccessReason) : null;
}

/** The only place that turns an API error into a small, switchable kind. */
export function classifyError(error: unknown): ApiFailure {
  if (!(error instanceof ApiError)) return { kind: "unknown" };
  const { status, code, details } = error;
  if (code === "network_error") return { kind: "network" };
  if (code === "timeout") return { kind: "timeout" };
  if (status === 401) return { kind: "session_lost" };
  if (status === 429) return { kind: "rate_limited" };
  if (status === 402) {
    const reason = gateReason(details);
    return reason ? { kind: "gate", reason } : { kind: "unknown" };
  }
  if (status === 409 && (code === "quiz_locked" || code === "already_subscribed")) {
    return { kind: "locked", code };
  }
  if (status === 422) return { kind: "validation", code, details };
  if (status === 502) {
    const hint = isRecord(details) ? details["hint"] : undefined;
    return { kind: "gateway", demoHint: hint === "demo_mode" };
  }
  if (status >= 500) return { kind: "server" };
  return { kind: "unknown" };
}

export interface GateTarget {
  path: string;
  /** Set when the reason needs a plain message instead of a screen of its own. */
  notice: "past_due" | null;
}

/** The only place that knows which screen each 402 reason belongs to. */
export function gateRoute(reason: AccessReason): GateTarget {
  switch (reason) {
    case "no_plan":
      return { path: ROUTES.quiz, notice: null };
    case "no_subscription":
      return { path: ROUTES.paywall, notice: null };
    case "past_due":
      return { path: ROUTES.paywall, notice: "past_due" };
    case "ended":
      return { path: ROUTES.home, notice: null };
  }
}

/** `quiz_incomplete` carries the missing ids in details.questionIds. */
export function missingQuestionIds(failure: ApiFailure): string[] {
  if (failure.kind !== "validation" || failure.code !== "quiz_incomplete") return [];
  const ids = isRecord(failure.details) ? failure.details["questionIds"] : undefined;
  return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === "string") : [];
}
