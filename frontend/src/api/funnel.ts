import { ApiError, apiRequest } from "./client";
import { createSession } from "./session";
import type {
  AnswerResult,
  AnswerValue,
  CheckoutCreated,
  CheckoutRequest,
  CheckoutStatus,
  CompleteResult,
  EventsStored,
  FunnelCopy,
  FunnelEvent,
  Gift,
  PlanAccess,
  PlanPreview,
  PricingResponse,
  QuizQuestion,
  QuizState,
  Subscription,
} from "./funnelTypes";

export { createSession };

const QUESTION_TYPES: readonly string[] = ["single", "multi", "grid", "scale", "interstitial"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const isString = (v: unknown): v is string => typeof v === "string";
const isIdLabel = (v: unknown): boolean =>
  isRecord(v) && isString(v["id"]) && isString(v["label"]);
const isList = (v: unknown, item: (x: unknown) => boolean): boolean =>
  Array.isArray(v) && v.every(item);

/** Checks only what the UI reads. An unknown shape is an error state, not a crash. */
export function isQuizQuestion(value: unknown): value is QuizQuestion {
  if (!isRecord(value)) return false;
  const { id, type, title } = value;
  if (!isString(id) || !isString(type) || !QUESTION_TYPES.includes(type) || !isString(title)) {
    return false;
  }
  switch (type) {
    case "single":
      return isList(value["options"], isIdLabel);
    case "multi":
      return typeof value["max"] === "number" && isList(value["options"], isIdLabel);
    case "grid":
      return isList(value["states"], isIdLabel) && isList(value["rows"], isIdLabel);
    case "scale":
      return (
        typeof value["min"] === "number" &&
        typeof value["max"] === "number" &&
        isString(value["minLabel"]) &&
        isString(value["maxLabel"])
      );
    default:
      return isString(value["body"]) && isString(value["cta"]);
  }
}

const invalidResponse = (): ApiError =>
  new ApiError(0, "invalid_response", "The server sent something we did not expect.");

export async function getQuiz(signal?: AbortSignal): Promise<QuizState> {
  const quiz = await apiRequest<QuizState>({ method: "GET", path: "/quiz", signal, auth: true });
  if (!Array.isArray(quiz.questions) || !quiz.questions.every(isQuizQuestion)) {
    throw invalidResponse();
  }
  return quiz;
}

export function putAnswer(
  questionId: string,
  value: AnswerValue | null,
  signal?: AbortSignal,
): Promise<AnswerResult> {
  return apiRequest<AnswerResult>({
    method: "PUT",
    path: `/quiz/answers/${encodeURIComponent(questionId)}`,
    body: { value },
    signal,
    auth: true,
  });
}

export function completeQuiz(signal?: AbortSignal): Promise<CompleteResult> {
  return apiRequest<CompleteResult>({ method: "POST", path: "/quiz/complete", signal, auth: true });
}

export function getPlanPreview(signal?: AbortSignal): Promise<PlanPreview> {
  return apiRequest<PlanPreview>({ method: "GET", path: "/plan/preview", signal, auth: true });
}

export function getGift(signal?: AbortSignal): Promise<Gift> {
  return apiRequest<Gift>({ method: "GET", path: "/plan/gift", signal, auth: true });
}

/** Needs P2 (`GET /api/funnel-copy`). Session required, not behind the gate. */
export function getFunnelCopy(signal?: AbortSignal): Promise<FunnelCopy> {
  return apiRequest<FunnelCopy>({ method: "GET", path: "/funnel-copy", signal, auth: true });
}

/** Pricing with the session attached, so `firstRenewalDate` is filled. */
export function getPricing(signal?: AbortSignal): Promise<PricingResponse> {
  return apiRequest<PricingResponse>({ method: "GET", path: "/pricing", signal, auth: true });
}

export function startDemo(body: CheckoutRequest, signal?: AbortSignal): Promise<Subscription> {
  return apiRequest<Subscription>({ method: "POST", path: "/billing/demo", body, signal, auth: true });
}

export function createCheckout(
  body: CheckoutRequest,
  signal?: AbortSignal,
): Promise<CheckoutCreated> {
  return apiRequest<CheckoutCreated>({
    method: "POST",
    path: "/billing/checkout",
    body,
    signal,
    auth: true,
  });
}

export function getCheckoutStatus(checkoutId: string, signal?: AbortSignal): Promise<CheckoutStatus> {
  return apiRequest<CheckoutStatus>({
    method: "GET",
    path: `/billing/checkout/${encodeURIComponent(checkoutId)}`,
    signal,
    auth: true,
  });
}

/** `GET /api/plan`: 200 means subscribed; 402 carries the reason (see errors.ts). */
export function probeAccess(signal?: AbortSignal): Promise<PlanAccess> {
  return apiRequest<PlanAccess>({ method: "GET", path: "/plan", signal, auth: true });
}

export function postEvents(events: FunnelEvent[], signal?: AbortSignal): Promise<EventsStored> {
  return apiRequest<EventsStored>({
    method: "POST",
    path: "/events",
    body: { events },
    signal,
    auth: true,
  });
}
