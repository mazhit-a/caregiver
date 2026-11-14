// Hand-written to match backend/app/presentation/api/schemas (camelCase).
// The fixture contract test in funnel.test.ts compares these key lists with real responses.
import type { PricingResponse } from "./types";

export type { PricingPlan, PricingResponse } from "./types";

// ---- Quiz ---------------------------------------------------------------

export interface QuizOption {
  id: string;
  label: string;
  /** Exclusive option in a multi question ("None of these yet"). */
  exclusive?: boolean;
}

interface QuestionBase {
  id: string;
  title: string;
  subtitle?: string;
  /** True for health answers (Q3, Q5): shown with the privacy note, never logged. */
  healthData: boolean;
}

export interface SingleQuestion extends QuestionBase {
  type: "single";
  options: QuizOption[];
}

export interface MultiQuestion extends QuestionBase {
  type: "multi";
  max: number;
  skippable?: boolean;
  options: QuizOption[];
}

export interface GridRow {
  id: string;
  label: string;
  hint: string;
}

export interface GridQuestion extends QuestionBase {
  type: "grid";
  states: { id: string; label: string }[];
  rows: GridRow[];
}

export interface ScaleQuestion extends QuestionBase {
  type: "scale";
  min: number;
  max: number;
  minLabel: string;
  maxLabel: string;
}

export interface InterstitialQuestion extends QuestionBase {
  type: "interstitial";
  body: string;
  cta: string;
  /** Ignored by the UI (the Ollie image is a fixed design choice). */
  speaker?: string;
}

export type QuizQuestion =
  | SingleQuestion
  | MultiQuestion
  | GridQuestion
  | ScaleQuestion
  | InterstitialQuestion;

/** Answer values: a choice id, a list of ids, a grid map (row id to state id) or a scale number. */
export type AnswerValue = string | string[] | Record<string, string> | number;

export interface QuizState {
  questions: QuizQuestion[];
  answers: Record<string, AnswerValue>;
  branch: string | null;
  lastQuestionId: string | null;
  completed: boolean;
  locked: boolean;
}

export interface AnswerResult {
  questionId: string;
  branch: string | null;
  tags: string[];
  lastQuestionId: string | null;
}

export interface SessionCreated {
  token: string;
  timezone: string;
}

export interface CompleteResult {
  completed: boolean;
  completedAt: string;
  rulesVersion: number;
  contentVersion: string;
}

// ---- Plan preview and gift -----------------------------------------------

export interface PlanLesson {
  id: string;
  title: string;
  minutes: number;
  built: boolean;
}

export interface PlanModule {
  id: string;
  title: string;
  reason: string;
  status: string;
  inFirst30Days: boolean;
  lessons: PlanLesson[];
}

export interface QuickGuide {
  id: string;
  title: string;
  highlight: boolean;
}

export interface Pace {
  lessonsPerWeek: number;
  minutesPerLesson: number;
  label: string;
}

export interface Readiness {
  modulesTotal: number;
  lessonsTotal: number;
}

export interface BeforeAfter {
  before: string;
  after: string;
}

export interface PlanPreview {
  planIntro: string;
  whatWeHeard: string[];
  beforeAfter: BeforeAfter;
  modules: PlanModule[];
  first30Days: string[];
  firstLessonId: string;
  quickGuides: QuickGuide[];
  loaderLines: string[];
  pace: Pace;
  readiness: Readiness;
  rulesVersion: number;
  contentVersion: string;
  builtAt: string;
}

export interface GiftPhrase {
  id: string;
  text: string;
  when: string;
}

export interface Gift {
  title: string;
  intro: string;
  phrases: GiftPhrase[];
  footer: string;
}

// ---- Funnel copy (P2, GET /api/funnel-copy) -------------------------------
// PROVISIONAL: P2 is not built yet and the plan leaves the exact shape to its implementer.
// This follows the "required content" list of P2. Re-check against the real response when P2 lands.

export interface DisclosureSegment {
  text: string;
  strong: boolean;
}

export interface PaywallPlanCopy {
  id: string;
  label: string;
  priceToday: string;
  detail: string;
  disclosure: DisclosureSegment[];
  consentLabel: string;
  payButtonLabel: string;
}

export interface FunnelCopy {
  loader: { title: string };
  planPreview: { title: string; cta: string };
  paywall: {
    headline: string;
    subhead: string;
    includes: string[];
    consentRequiredError: string;
    states: { success: string; returnedCanceled: string };
    defaultPlanId: string;
    plans: PaywallPlanCopy[];
  };
}

// ---- Billing ---------------------------------------------------------------

export interface Subscription {
  status: string;
  planId: string | null;
  source: string | null;
  currentPeriodStart: string | null;
  currentPeriodEnd: string | null;
  renewalCount: number;
  autoRenewConsentAt: string | null;
  billingSync: string;
}

export interface CheckoutRequest {
  autoRenewConsent: boolean;
  planId?: string;
}

export interface CheckoutCreated {
  checkoutId: string;
  url: string;
}

export interface CheckoutStatus {
  paid: boolean;
  message: string | null;
  subscription: Subscription;
}

/** `GET /api/plan`, the lightest gated read (used as the access probe). */
export interface PlanAccess {
  modules: {
    id: string;
    title: string;
    reason: string;
    lessons: {
      id: string;
      title: string;
      minutes: number;
      status: string;
      unlockOn: string | null;
    }[];
  }[];
  heroLessonId: string | null;
  lessonsPerWeek: number;
}

export interface FunnelEvent {
  name: string;
  props?: Record<string, string | number | boolean | null>;
}

export interface EventsStored {
  stored: number;
}

// ---- Key lists used by the fixture contract test ---------------------------

type Keys<T> = readonly (keyof T)[];

export const SESSION_KEYS = ["token", "timezone"] as const satisfies Keys<SessionCreated>;
export const QUIZ_STATE_KEYS = [
  "questions",
  "answers",
  "branch",
  "lastQuestionId",
  "completed",
  "locked",
] as const satisfies Keys<QuizState>;
export const ANSWER_RESULT_KEYS = [
  "questionId",
  "branch",
  "tags",
  "lastQuestionId",
] as const satisfies Keys<AnswerResult>;
export const COMPLETE_KEYS = [
  "completed",
  "completedAt",
  "rulesVersion",
  "contentVersion",
] as const satisfies Keys<CompleteResult>;
export const PLAN_PREVIEW_KEYS = [
  "planIntro",
  "whatWeHeard",
  "beforeAfter",
  "modules",
  "first30Days",
  "firstLessonId",
  "quickGuides",
  "loaderLines",
  "pace",
  "readiness",
  "rulesVersion",
  "contentVersion",
  "builtAt",
] as const satisfies Keys<PlanPreview>;
export const PLAN_MODULE_KEYS = [
  "id",
  "title",
  "reason",
  "status",
  "inFirst30Days",
  "lessons",
] as const satisfies Keys<PlanModule>;
export const PLAN_LESSON_KEYS = ["id", "title", "minutes", "built"] as const satisfies Keys<PlanLesson>;
export const QUICK_GUIDE_KEYS = ["id", "title", "highlight"] as const satisfies Keys<QuickGuide>;
export const PACE_KEYS = ["lessonsPerWeek", "minutesPerLesson", "label"] as const satisfies Keys<Pace>;
export const READINESS_KEYS = ["modulesTotal", "lessonsTotal"] as const satisfies Keys<Readiness>;
export const BEFORE_AFTER_KEYS = ["before", "after"] as const satisfies Keys<BeforeAfter>;
export const GIFT_KEYS = ["title", "intro", "phrases", "footer"] as const satisfies Keys<Gift>;
export const GIFT_PHRASE_KEYS = ["id", "text", "when"] as const satisfies Keys<GiftPhrase>;
export const SUBSCRIPTION_KEYS = [
  "status",
  "planId",
  "source",
  "currentPeriodStart",
  "currentPeriodEnd",
  "renewalCount",
  "autoRenewConsentAt",
  "billingSync",
] as const satisfies Keys<Subscription>;
export const PRICING_KEYS = ["currency", "defaultPlanId", "plans"] as const satisfies Keys<PricingResponse>;
export const PLAN_ACCESS_KEYS = [
  "modules",
  "heroLessonId",
  "lessonsPerWeek",
] as const satisfies Keys<PlanAccess>;
export const EVENTS_KEYS = ["stored"] as const satisfies Keys<EventsStored>;
export const FUNNEL_COPY_KEYS = ["loader", "planPreview", "paywall"] as const satisfies Keys<FunnelCopy>;
