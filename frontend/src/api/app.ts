/** One typed function per app endpoint (after the paywall). Session token on every call except the public card. */
import type {
  AnswerBody,
  AnswerResult,
  AppCopy,
  CancelPreview,
  CancelResult,
  CareCard,
  CardSnapshot,
  CheckinBody,
  CheckinResult,
  ClearData,
  CoursePlan,
  Demo,
  GentleExit,
  KnownScreen,
  Lesson,
  LessonComplete,
  LessonProgress,
  Phrase,
  Phrases,
  PreviousTurn,
  Profile,
  ProfileBody,
  RoleplayContext,
  RoleplayFinish,
  RoleplayStart,
  RoleplayTurn,
  SavePhraseBody,
  ScreenOut,
  Skills,
  Subscription,
  Today,
  VisitSheet,
  VisitSheetBody,
} from "./appTypes";
import { SCREEN_TYPES } from "./appTypes";
import { ApiError, apiGet, apiRequest } from "./client";

/** A role-play turn may take the server's whole 12 s budget before it answers `fallback`. */
export const TURN_TIMEOUT_MS = 15_000;

type Method = "GET" | "POST" | "PUT" | "DELETE";

function call<T>(
  method: Method,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
  timeoutMs?: number,
): Promise<T> {
  return apiRequest<T>({ method, path, body, signal, auth: true, timeoutMs });
}

const enc = encodeURIComponent;

// ---- screen guard -------------------------------------------------------------

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Checks the fields the player reads for each of the seven screen types. */
export function isKnownScreen(value: unknown): value is KnownScreen {
  if (!isRecord(value) || typeof value["id"] !== "string") return false;
  const type = value["type"];
  if (typeof type !== "string" || !(SCREEN_TYPES as readonly string[]).includes(type)) return false;
  switch (type) {
    case "setup_question":
      return Array.isArray(value["options"]);
    case "scenario":
      return Array.isArray(value["answers"]) && isRecord(value["verdictLabels"]);
    case "learn":
      return typeof value["title"] === "string";
    case "phrases_review":
      return Array.isArray(value["phrases"]);
    case "roleplay":
      return (
        Array.isArray(value["rounds"]) && isRecord(value["labels"]) && isRecord(value["summary"])
      );
    case "plan":
      return isRecord(value["ifThen"]) && isRecord(value["doNow"]);
    default:
      return typeof value["skillLine"] === "string";
  }
}

/** An unknown or malformed screen becomes a typed "can't be shown" state, never a crash. */
export function toScreen(value: unknown): ScreenOut {
  if (isKnownScreen(value)) return value;
  const screenId = isRecord(value) && typeof value["id"] === "string" ? value["id"] : "unknown";
  return { id: screenId, type: "unknown" };
}

// ---- reads --------------------------------------------------------------------

export const getAppCopy = (signal?: AbortSignal): Promise<AppCopy> =>
  call("GET", "/app-copy", undefined, signal);
export const getToday = (signal?: AbortSignal): Promise<Today> =>
  call("GET", "/today", undefined, signal);
/** The in-app course (`GET /plan`). `probeAccess` in funnel.ts is the same call used as a gate probe. */
export const getPlan = (signal?: AbortSignal): Promise<CoursePlan> =>
  call("GET", "/plan", undefined, signal);

export async function getLesson(lessonId: string, signal?: AbortSignal): Promise<Lesson> {
  const lesson = await call<Lesson>("GET", `/lessons/${enc(lessonId)}`, undefined, signal);
  if (!Array.isArray(lesson.screens)) {
    throw new ApiError(0, "invalid_response", "The server sent something we did not expect.");
  }
  return { ...lesson, screens: lesson.screens.map(toScreen) };
}

export const answerLesson = (
  lessonId: string,
  body: AnswerBody,
  signal?: AbortSignal,
): Promise<AnswerResult> => call("POST", `/lessons/${enc(lessonId)}/answers`, body, signal);

export const completeLesson = (lessonId: string, signal?: AbortSignal): Promise<LessonComplete> =>
  call("POST", `/lessons/${enc(lessonId)}/complete`, undefined, signal);

/** Remembers the step the learner is on ("continue where you left off"). */
export const putLessonProgress = (
  lessonId: string,
  step: number,
  signal?: AbortSignal,
): Promise<LessonProgress> => call("PUT", `/lessons/${enc(lessonId)}/progress`, { step }, signal);

// ---- role-play ------------------------------------------------------------------

export const startRoleplay = (
  lessonId: string,
  context: RoleplayContext,
  signal?: AbortSignal,
): Promise<RoleplayStart> => call("POST", "/roleplay/start", { lessonId, context }, signal);

/** The reply text goes only into this request body: never into a URL, storage or a log. */
export const submitTurn = (
  runId: string,
  turn: { round: number; reply: string; previousTurns: PreviousTurn[] },
  signal?: AbortSignal,
): Promise<RoleplayTurn> =>
  call("POST", `/roleplay/${enc(runId)}/turn`, turn, signal, TURN_TIMEOUT_MS);

export const finishRoleplay = (
  runId: string,
  phrases: { reply: string; betterPhrase: string }[],
  signal?: AbortSignal,
): Promise<RoleplayFinish> => call("POST", `/roleplay/${enc(runId)}/finish`, { phrases }, signal);

// ---- phrases, check-ins, skills -------------------------------------------------------

export const listPhrases = (signal?: AbortSignal): Promise<Phrases> =>
  call("GET", "/phrases", undefined, signal);
export const savePhrase = (body: SavePhraseBody, signal?: AbortSignal): Promise<Phrase> =>
  call("POST", "/phrases", body, signal);
/** 204: resolves to undefined. */
export const deletePhrase = (phraseId: string, signal?: AbortSignal): Promise<void> =>
  call("DELETE", `/phrases/${enc(phraseId)}`, undefined, signal);
export const submitCheckin = (body: CheckinBody, signal?: AbortSignal): Promise<CheckinResult> =>
  call("POST", "/checkins", body, signal);
export const getSkills = (signal?: AbortSignal): Promise<Skills> =>
  call("GET", "/skills", undefined, signal);

// ---- profile, care card, visit sheet -----------------------------------------------------

export const getProfile = (signal?: AbortSignal): Promise<Profile> =>
  call("GET", "/profile", undefined, signal);
export const putProfile = (body: ProfileBody, signal?: AbortSignal): Promise<Profile> =>
  call("PUT", "/profile", body, signal);

export const getCareCard = (signal?: AbortSignal): Promise<CareCard> =>
  call("GET", "/care-card", undefined, signal);
export const publishCareCard = (phraseIds: string[], signal?: AbortSignal): Promise<CareCard> =>
  call("POST", "/care-card", { phraseIds }, signal);
export const updateCareCard = (phraseIds: string[], signal?: AbortSignal): Promise<CareCard> =>
  call("PUT", "/care-card", { phraseIds }, signal);
export const revokeCareCard = (signal?: AbortSignal): Promise<CareCard> =>
  call("DELETE", "/care-card", undefined, signal);

/** Public: no session token is read or sent, so a 401 can never clear anything. */
export const getPublicCard = (cardId: string, signal?: AbortSignal): Promise<CardSnapshot> =>
  apiGet(`/cards/${enc(cardId)}`, signal);

export const getVisitSheet = (signal?: AbortSignal): Promise<VisitSheet> =>
  call("GET", "/visit-sheet", undefined, signal);
export const putVisitSheet = (body: VisitSheetBody, signal?: AbortSignal): Promise<VisitSheet> =>
  call("PUT", "/visit-sheet", body, signal);

// ---- billing, exit ---------------------------------------------------------------------------

export const getSubscription = (signal?: AbortSignal): Promise<Subscription> =>
  call("GET", "/billing/subscription", undefined, signal);
export const getCancelPreview = (signal?: AbortSignal): Promise<CancelPreview> =>
  call("GET", "/billing/cancel-preview", undefined, signal);
export const cancelSubscription = (signal?: AbortSignal): Promise<CancelResult> =>
  call("POST", "/billing/cancel", undefined, signal);
export const gentleExit = (signal?: AbortSignal): Promise<GentleExit> =>
  call("POST", "/exit/gentle", undefined, signal);
/** `DELETE /session`: the caller clears the token only after this resolves. */
export const clearMyData = (signal?: AbortSignal): Promise<ClearData> =>
  call("DELETE", "/session", undefined, signal);

// ---- demo controls (404 when the server has them off) -------------------------------------------

export const getDemo = (signal?: AbortSignal): Promise<Demo> =>
  call("GET", "/demo", undefined, signal);
export const demoNextDay = (signal?: AbortSignal): Promise<Demo> =>
  call("POST", "/demo/next-day", undefined, signal);
export const demoJumpToRenewal = (signal?: AbortSignal): Promise<Demo> =>
  call("POST", "/demo/jump-to-renewal", undefined, signal);
export const demoFailNextPayment = (signal?: AbortSignal): Promise<Demo> =>
  call("POST", "/demo/fail-next-payment", undefined, signal);
