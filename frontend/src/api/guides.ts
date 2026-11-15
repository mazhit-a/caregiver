/** Public quick guides. The session token is sent only when one is stored (it only personalises the wording). */
import { ApiError, apiRequest } from "./client";
import { clearToken, getToken } from "./session";

export type GuideUrgency = "emergency" | "urgent" | "planning" | "support";

export interface GuideSummary {
  id: string;
  title: string;
  summary: string;
  urgency: GuideUrgency;
}

export interface GuideList {
  guides: GuideSummary[];
}

export interface Guide extends GuideSummary {
  callNowTitle: string;
  callNow: string[];
  stepsTitle: string;
  steps: { title: string; text: string }[];
  thenTitle: string;
  then: string[];
  dontTitle: string;
  dont: string[];
  resourcesTitle: string;
  resources: { label: string; number: string; tel: string }[];
  sources: { name: string; url: string }[];
  footer: string;
}

const URGENCIES: readonly string[] = ["emergency", "urgent", "planning", "support"];

function rec(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
const str = (v: unknown): v is string => typeof v === "string";
const strs = (v: unknown): v is string[] => Array.isArray(v) && v.every(str);
const listOf = (v: unknown, ok: (x: Record<string, unknown>) => boolean): boolean =>
  Array.isArray(v) && v.every((x) => rec(x) && ok(x));

export function isGuideSummary(v: unknown): v is GuideSummary {
  return rec(v) && str(v["id"]) && str(v["title"]) && str(v["summary"]) && str(v["urgency"]) && URGENCIES.includes(v["urgency"]);
}

export function isGuideList(v: unknown): v is GuideList {
  return rec(v) && Array.isArray(v["guides"]) && v["guides"].every(isGuideSummary);
}

export function isGuide(v: unknown): v is Guide {
  return (
    isGuideSummary(v) &&
    rec(v) &&
    str(v["callNowTitle"]) && strs(v["callNow"]) &&
    str(v["stepsTitle"]) && listOf(v["steps"], (s) => str(s["title"]) && str(s["text"])) &&
    str(v["thenTitle"]) && strs(v["then"]) &&
    str(v["dontTitle"]) && strs(v["dont"]) &&
    str(v["resourcesTitle"]) &&
    listOf(v["resources"], (r) => str(r["label"]) && str(r["number"]) && str(r["tel"])) &&
    listOf(v["sources"], (s) => str(s["name"]) && str(s["url"])) &&
    str(v["footer"])
  );
}

function checked<T>(value: unknown, guard: (v: unknown) => v is T): T {
  if (!guard(value)) throw new ApiError(0, "invalid_response", "The server sent something unexpected.");
  return value;
}

/** A stale stored token answers 401 (and is cleared by the client); the guides are public, so ask once more without it. */
async function publicGet<T>(path: string, guard: (v: unknown) => v is T, signal?: AbortSignal): Promise<T> {
  const hadToken = getToken() !== null;
  try {
    return checked(await apiRequest<unknown>({ method: "GET", path, signal, auth: true }), guard);
  } catch (error) {
    if (hadToken && error instanceof ApiError && error.status === 401) {
      clearToken();
      return checked(await apiRequest<unknown>({ method: "GET", path, signal, auth: false }), guard);
    }
    throw error;
  }
}

export const getGuides = (signal?: AbortSignal): Promise<GuideList> => publicGet("/guides", isGuideList, signal);
export const getGuide = (id: string, signal?: AbortSignal): Promise<Guide> =>
  publicGet(`/guides/${encodeURIComponent(id)}`, isGuide, signal);
