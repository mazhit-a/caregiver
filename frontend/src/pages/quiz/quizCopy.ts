// Quiz-only strings with no placeholder. Mirrors content/funnel-copy.json (locked by quiz.test.tsx).
export const QUIZ_HEALTH_NOTE = "This page has no ad tracking. Saved privately to this session.";
export const QUIZ_UI = {
  loading: "Loading your quiz…",
  retry: "Try again",
  saving: "Saving…",
  progressLabel: (n: number, total: number): string => `${n} of ${total}`,
} as const;
