// UI-owned strings of the Plan (course) view. Anything with a placeholder (the title, the
// subtitle, the quick-guide caption, module reasons, "Mom's plan: 0 of 12 ...") comes from the API.

/** The one quick guide that opens the help sheet. Mirrors content/plan-rules.json quickGuides[].id (locked by plan.test.ts). */
export const QG_LIMIT_ID = "qg_limit";

export const PLAN_TEXT = {
  loadingHeading: "Plan",
  what: "course",
  viewLegend: "Course view",
  viewPath: "Path",
  viewAll: "All modules",
  pathLabel: "Your lessons, in order",
  after30Title: "After your first 30 days",
  /** Fallback only; the server's readiness text is shown when present. */
  progressLabel: "Lessons done",
  upNext: "Up next",
  comingLater: "Coming later",
  current: "In progress",
  start: "Start",
  continue: "Continue",
  done: "Done",
  opensSoon: "Opens soon",
  forNow: "For now",
  seeInPath: "See in the path",
  openLesson: "Open the first lesson",
} as const;

export const lessonCount = (n: number): string => `${n} ${n === 1 ? "lesson" : "lessons"}`;
export const moduleKicker = (position: number, lessons: number): string =>
  `Module ${position} · ${lessonCount(lessons)}`;
export const doneOf = (done: number, total: number): string => `${done} of ${total} done`;
export const lessonsDoneOf = (done: number, total: number): string =>
  `${done} of ${total} ${total === 1 ? "lesson" : "lessons"} done`;
export const opensOn = (date: string): string => `Opens ${date}`;
export const minutesLabel = (m: number): string => `${m} min`;
