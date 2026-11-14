/** camelCase types of the app endpoints (after the paywall). Shapes follow the backend schemas. */
import type { Subscription } from "./funnelTypes";

export type { Subscription };

type Status = "locked" | "available" | "in_progress" | "done" | "coming_later";

// ---- GET /app-copy ----------------------------------------------------------

export interface AppCopy {
  nav: { today: string; plan: string; profilePage: string; skills: string; settings: string };
  plan: { title: string; subtitle: string; quickGuidesTitle: string; quickGuidesCaption: string };
  profile: {
    title: string;
    privacyNote: string;
    worksTitle: string;
    aboutTitle: string;
    enjoysTitle: string;
    calmsTitle: string;
    avoidTitle: string;
    rhythmTitle: string;
    contactsTitle: string;
    emptyPhrases: string;
    editNote: string;
  };
  careCard: { title: string; purpose: string; sharingSentence: string };
  visitSheet: { title: string; subtitle: string };
  skills: { title: string; subtitle: string };
  settings: { title: string; gentleExitEntry: string; gentleExitHint: string };
  welcome: { title: string; body: string; nameLabel: string };
}

// ---- GET /today -------------------------------------------------------------

export interface Choice {
  id: string;
  label: string;
}

export interface PlanQuote {
  cue: string;
  response: string;
  reset: string | null;
}

export interface CheckinCard {
  planId: string;
  question: string;
  options: Choice[];
  followUp: { ifAnswer: string; question: string; options: Choice[] } | null;
  plan: PlanQuote;
}

export interface PracticeRound {
  lessonId: string;
  title: string;
  roundsTotal: number;
  variant: string | null;
  context: "practice_round";
}

export interface TodayLesson {
  lessonId: string;
  title: string;
  moduleId: string;
  reason: string;
  status: Status;
  unlockOn: string | null;
  minutes: number;
  skillLabel: string | null;
}

export interface Today {
  title: string;
  order: string[];
  checkIn: CheckinCard | null;
  practiceRound: PracticeRound | null;
  careCardNudge: { newPhraseCount: number; text: string } | null;
  nextStep: {
    kind: "lesson" | "rest" | "all_done";
    message: string | null;
    lesson: TodayLesson | null;
    unlockText: string | null;
  };
  weeklyRhythm: { done: number; target: number; text: string };
  readiness: { done: number; total: number; text: string };
  subscriptionNotice: { kind: "renews_on" | "renewed" | "ends_on"; on: string; text: string } | null;
  welcomeBack: { title: string; body: string } | null;
  visitSheetLink: { label: string; path: string };
  demo: {
    label: string;
    appNow: string;
    appToday: string;
    clockOffsetSeconds: number;
    controls: Choice[];
  } | null;
}

// ---- GET /plan (the in-app course) ------------------------------------------

export interface CoursePlan {
  modules: {
    id: string;
    title: string;
    reason: string;
    lessons: {
      id: string;
      title: string;
      minutes: number;
      status: Status;
      unlockOn: string | null;
    }[];
  }[];
  heroLessonId: string | null;
  lessonsPerWeek: number;
}

// ---- lessons ----------------------------------------------------------------

export interface PatternStep {
  id: string;
  label: string;
  example: string;
}
export interface Pattern {
  name: string;
  steps: PatternStep[];
}

export interface SetupQuestionScreen {
  id: string;
  type: "setup_question";
  speaker: string;
  text: string;
  question: string;
  options: Choice[];
}
export interface ScenarioScreen {
  id: string;
  type: "scenario";
  intro?: string | null;
  setup: string;
  line: string;
  question: string;
  answers: { id: string; text: string }[];
  verdictLabels: Record<string, string>;
  afterChoice: string;
  saveButton: string;
}
export interface LearnScreen {
  id: string;
  type: "learn";
  title: string;
  body?: string | null;
  bullets?: string[] | null;
  extra?: string | null;
  patternTip?: string | null;
  pattern?: Pattern | null;
  miniTask?: { question: string; options: Choice[] } | null;
}
export interface PhrasesReviewScreen {
  id: string;
  type: "phrases_review";
  title: string;
  intro: string;
  emptyText: string;
  phrases: { id: string; text: string; source: string; lessonId?: string | null }[];
}
export interface RoleplayScreen {
  id: string;
  type: "roleplay";
  title: string;
  intro: string;
  goals: string[];
  rounds: { stage: string; line: string; mood: string }[];
  labels: { partner: string; notSaved: string; thinking: string; aiDown: string };
  summary: { title: string; bestPhraseLabel: string; saveButton: string; againButton: string };
}
export interface PlanScreen {
  id: string;
  type: "plan";
  title: string;
  ifThen: {
    cue: string;
    responseLabel: string;
    responseEditable: boolean;
    resetLabel: string;
    resetFrom: string;
  };
  doNow: { title: string; text: string; action: string; button: string };
  remindButton: string;
  doneButton: string;
  noteTemplate: { title: string; example: string };
}
export interface WrapScreen {
  id: string;
  type: "wrap";
  skillLine: string;
  phraseLine: string;
  patternLine: string;
  confidenceCheck?: { title: string; scale: string; items: Choice[] } | null;
  tomorrowLine: string;
  nextLine: string;
}

export type KnownScreen =
  | SetupQuestionScreen
  | ScenarioScreen
  | LearnScreen
  | PhrasesReviewScreen
  | RoleplayScreen
  | PlanScreen
  | WrapScreen;

/** A screen type the browser does not know: shown as "this screen can't be shown", never a crash. */
export interface UnknownScreen {
  id: string;
  type: "unknown";
}

/** `ScreenOut` after the runtime guard (see `toScreen` in app.ts). */
export type ScreenOut = KnownScreen | UnknownScreen;

export const SCREEN_TYPES = [
  "setup_question",
  "scenario",
  "learn",
  "phrases_review",
  "roleplay",
  "plan",
  "wrap",
] as const satisfies readonly KnownScreen["type"][];

export interface Lesson {
  id: string;
  moduleId: string;
  title: string;
  minutes: number;
  skill: string;
  skillLabel: string;
  variant: string | null;
  unlockOn: string;
  pattern: Pattern;
  screens: ScreenOut[];
  progress: { step: number; startedAt: string; doneAt: string | null };
  recap?: { fromLessonId: string; text: string } | null;
}

export interface AnswerBody {
  screenId: string;
  value: unknown;
}

export interface SetupResult {
  variant: string;
}
export interface ScenarioResult {
  answerId: string;
  verdict: string;
  feedback: string;
  savePhrase: boolean;
}
export interface MiniTaskResult {
  optionId: string;
  response: string | null;
  correct?: boolean;
}
export interface PlanResult {
  ifThen: { cue: string; response: string; reset: string | null };
  task: { text: string; action: string };
  reminder: {
    title: string;
    description: string;
    startsAt: string;
    timezone: string;
    url: string;
  };
}
export interface WrapResult {
  saved: boolean;
  ratings: Record<string, number>;
}

/** The answer's `result` depends on the screen type (backend `AnswerResponse`). */
export interface AnswerResult {
  screenId: string;
  type: string;
  result: Record<string, unknown>;
}

export interface LessonComplete {
  lessonId: string;
  doneAt: string;
  wrap: Omit<WrapScreen, "confidenceCheck"> & { confidenceCheck?: WrapScreen["confidenceCheck"] } | null;
  nextLesson: { id: string; title: string; moduleId: string; reason: string; unlockOn: string } | null;
  allDoneLine: string | null;
}

export interface LessonProgress {
  step: number;
  startedAt: string;
  doneAt: string | null;
}

// ---- role-play --------------------------------------------------------------

export type RoleplayContext = "lesson" | "practice_round";

export interface RoleplayStart {
  runId: string;
  lessonId: string;
  context: RoleplayContext;
  variant: string | null;
  roundsTotal: number;
  rounds: { stage: string; line: string; mood: string }[];
  title: string;
  goals: string[];
  intro: string | null;
  labels: Record<string, string>;
}

export interface PreviousTurn {
  parent: string;
  caregiver: string;
  score: number;
}

export interface CoachPanel {
  aiGenerated: true;
  score: number;
  goals: { notice: boolean; reassure: boolean; offer: boolean };
  argued: boolean;
  flags: string[];
  tip: string;
  betterPhrase: string;
  parentReaction: string;
  parentMood: string;
}

export interface CrisisResource {
  id: string;
  name: string;
  phone: string;
  description: string;
}

export interface FallbackScenario {
  id: string;
  setup: string;
  line: string;
  answers: { text: string; verdict: string; feedback: string }[];
}

export interface RoleplayTurn {
  mode: "ai" | "fallback" | "safety";
  runMode: "ai" | "fallback";
  round: number;
  roundsTotal: number;
  coach: CoachPanel | null;
  kind: "crisis" | "emergency" | null;
  resources: CrisisResource[];
  emergencyText: string | null;
  fallbackScenarios: FallbackScenario[];
}

export interface RoleplayFinish {
  runId: string;
  mode: "ai" | "fallback";
  finishedAt: string;
  summary: {
    firstScore: number | null;
    lastScore: number | null;
    improved: boolean;
    noticeTurns: number;
    reassureTurns: number;
    offerTurns: number;
  };
  scores: number[];
  firstVsLast: string | null;
  bestPhrase: string | null;
}

// ---- phrases, check-ins, skills ----------------------------------------------

export interface Phrase {
  id: string;
  text: string;
  source: "scenario" | "roleplay" | "gift";
  lessonId: string | null;
  savedAt: string;
}
export interface Phrases {
  phrases: Phrase[];
}
export interface SavePhraseBody {
  text: string;
  source: Phrase["source"];
  lessonId?: string;
}

export interface CheckinBody {
  planId: string;
  cameUp: string;
  outcome?: "helped" | "partly" | "didnt_help";
  doctorNote?: { addToVisitSheet: boolean; text?: string };
}
export interface CheckinResult {
  planId: string;
  cameUp: string;
  outcome: "helped" | "partly" | "didnt_help" | null;
  responseText: string | null;
  followUps: { title: string; text: string }[];
  plan: PlanQuote;
  observationAdded: boolean;
  taskDone: boolean;
}

export interface Skills {
  skills: {
    id: string;
    label: string;
    roleplay: { runs: number; firstScore: number | null; latestScore: number | null; maxScore: number } | null;
    scenarios: { practised: number; best: number } | null;
  }[];
  confidence: {
    day0: number | null;
    first: Record<string, number> | null;
    latest: Record<string, number> | null;
  };
  counts: { scenariosPractised: number; phrasesSaved: number; tasksTried: number; tasksHelped: number };
  next: {
    lessonId: string;
    title: string;
    moduleId: string;
    reason: string;
    status: Status;
    unlockOn: string | null;
  } | null;
}

// ---- profile, care card, visit sheet -------------------------------------------

export interface Contact {
  name: string;
  phone: string;
  role: string | null;
}
export interface Profile {
  displayName: string | null;
  enjoys: string[];
  calms: string[];
  avoid: string[];
  rhythm: string;
  contacts: Contact[];
  caregiverFirstName: string | null;
  updatedAt: string | null;
}
export interface ProfileBody {
  displayName?: string | null;
  enjoys?: string[];
  calms?: string[];
  avoid?: string[];
  rhythm?: string;
  contacts?: { name: string; phone: string; role?: string | null }[];
  caregiverFirstName?: string | null;
}

export interface CardSnapshot {
  displayName: string;
  enjoys: string[];
  calms: string[];
  avoid: string[];
  rhythm: string;
  contacts: Contact[];
  helplines: { name: string; phone: string; description: string }[];
  phrases: string[];
  updatedOn: string;
  caregiverFirstName: string | null;
}

export type CardStatus = "not_published" | "published" | "update_available" | "revoked";

export interface CareCard {
  status: CardStatus;
  link: string | null;
  published: CardSnapshot | null;
  preview: CardSnapshot;
  chosenPhraseIds: string[];
  availablePhrases: { id: string; text: string }[];
  newPhraseCount: number;
  publishedAt: string | null;
  updatedAt: string | null;
  lastOpenedAt: string | null;
  revokedAt: string | null;
}

export interface VisitSheet {
  doctor: string | null;
  visitDate: string | null;
  familyNotes: string;
  questions: { id: string | null; text: string; custom: boolean }[];
  bank: { id: string; text: string }[];
  suggestedNotes: { id: string; text: string; createdAt: string }[];
  footer: string;
  updatedAt: string | null;
}
export interface VisitSheetBody {
  doctor?: string | null;
  visitDate?: string | null;
  familyNotes?: string;
  questions?: ({ id: string } | { text: string })[];
}

// ---- billing, exit, demo ---------------------------------------------------------

export interface CancelPreview {
  planName: string;
  savedPhraseCount: number;
  careCardPublished: boolean;
  endDate: string | null;
  status: string;
}
export interface CancelResult {
  status: string;
  endDate: string | null;
}

export interface GentleExit {
  title: string;
  condolence: string;
  resourcesIntro: string;
  resources: {
    id: string;
    name: string;
    description: string;
    phone: string | null;
    url: string | null;
  }[];
}
export interface ClearData {
  message: string;
}

export interface Demo {
  demoControls: boolean;
  label: string;
  appNow: string;
  appToday: string;
  clockOffsetSeconds: number;
  subscriptionStatus: string;
  currentPeriodEnd: string | null;
  renewalCount: number;
  billingSync: string;
}

// ---- Key lists used by the fixture contract test ------------------------------------

type Keys<T> = readonly (keyof T)[];

export const APP_COPY_KEYS = [
  "nav", "plan", "profile", "careCard", "visitSheet", "skills", "settings", "welcome",
] as const satisfies Keys<AppCopy>;
export const TODAY_KEYS = [
  "title", "order", "checkIn", "practiceRound", "careCardNudge", "nextStep", "weeklyRhythm",
  "readiness", "subscriptionNotice", "welcomeBack", "visitSheetLink", "demo",
] as const satisfies Keys<Today>;
export const TODAY_LESSON_KEYS = [
  "lessonId", "title", "moduleId", "reason", "status", "unlockOn", "minutes", "skillLabel",
] as const satisfies Keys<TodayLesson>;
export const CHECKIN_CARD_KEYS = [
  "planId", "question", "options", "followUp", "plan",
] as const satisfies Keys<CheckinCard>;
export const PRACTICE_ROUND_KEYS = [
  "lessonId", "title", "roundsTotal", "variant", "context",
] as const satisfies Keys<PracticeRound>;
export const COURSE_PLAN_KEYS = [
  "modules", "heroLessonId", "lessonsPerWeek",
] as const satisfies Keys<CoursePlan>;
export const LESSON_KEYS = [
  "id", "moduleId", "title", "minutes", "skill", "skillLabel", "variant", "unlockOn", "pattern",
  "screens", "progress", "recap",
] as const satisfies Keys<Lesson>;
export const LESSON_COMPLETE_KEYS = [
  "lessonId", "doneAt", "wrap", "nextLesson", "allDoneLine",
] as const satisfies Keys<LessonComplete>;
export const ANSWER_RESULT_KEYS = ["screenId", "type", "result"] as const satisfies Keys<AnswerResult>;
export const SCENARIO_RESULT_KEYS = [
  "answerId", "verdict", "feedback", "savePhrase",
] as const satisfies Keys<ScenarioResult>;
export const PLAN_RESULT_KEYS = ["ifThen", "task", "reminder"] as const satisfies Keys<PlanResult>;
export const WRAP_RESULT_KEYS = ["saved", "ratings"] as const satisfies Keys<WrapResult>;
export const ROLEPLAY_START_KEYS = [
  "runId", "lessonId", "context", "variant", "roundsTotal", "rounds", "title", "goals", "intro",
  "labels",
] as const satisfies Keys<RoleplayStart>;
export const ROLEPLAY_TURN_KEYS = [
  "mode", "runMode", "round", "roundsTotal", "coach", "kind", "resources", "emergencyText",
  "fallbackScenarios",
] as const satisfies Keys<RoleplayTurn>;
export const COACH_PANEL_KEYS = [
  "aiGenerated", "score", "goals", "argued", "flags", "tip", "betterPhrase", "parentReaction",
  "parentMood",
] as const satisfies Keys<CoachPanel>;
export const ROLEPLAY_FINISH_KEYS = [
  "runId", "mode", "finishedAt", "summary", "scores", "firstVsLast", "bestPhrase",
] as const satisfies Keys<RoleplayFinish>;
export const PHRASE_KEYS = ["id", "text", "source", "lessonId", "savedAt"] as const satisfies Keys<Phrase>;
export const CHECKIN_RESULT_KEYS = [
  "planId", "cameUp", "outcome", "responseText", "followUps", "plan", "observationAdded", "taskDone",
] as const satisfies Keys<CheckinResult>;
export const SKILLS_KEYS = ["skills", "confidence", "counts", "next"] as const satisfies Keys<Skills>;
export const PROFILE_KEYS = [
  "displayName", "enjoys", "calms", "avoid", "rhythm", "contacts", "caregiverFirstName", "updatedAt",
] as const satisfies Keys<Profile>;
export const CARD_SNAPSHOT_KEYS = [
  "displayName", "enjoys", "calms", "avoid", "rhythm", "contacts", "helplines", "phrases",
  "updatedOn", "caregiverFirstName",
] as const satisfies Keys<CardSnapshot>;
export const CARE_CARD_KEYS = [
  "status", "link", "published", "preview", "chosenPhraseIds", "availablePhrases", "newPhraseCount",
  "publishedAt", "updatedAt", "lastOpenedAt", "revokedAt",
] as const satisfies Keys<CareCard>;
export const VISIT_SHEET_KEYS = [
  "doctor", "visitDate", "familyNotes", "questions", "bank", "suggestedNotes", "footer", "updatedAt",
] as const satisfies Keys<VisitSheet>;
export const CANCEL_PREVIEW_KEYS = [
  "planName", "savedPhraseCount", "careCardPublished", "endDate", "status",
] as const satisfies Keys<CancelPreview>;
export const CANCEL_RESULT_KEYS = ["status", "endDate"] as const satisfies Keys<CancelResult>;
export const GENTLE_EXIT_KEYS = [
  "title", "condolence", "resourcesIntro", "resources",
] as const satisfies Keys<GentleExit>;
export const DEMO_KEYS = [
  "demoControls", "label", "appNow", "appToday", "clockOffsetSeconds", "subscriptionStatus",
  "currentPeriodEnd", "renewalCount", "billingSync",
] as const satisfies Keys<Demo>;
export const LESSON_PROGRESS_KEYS = ["step", "startedAt", "doneAt"] as const satisfies Keys<LessonProgress>;
