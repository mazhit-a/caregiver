// UI-owned strings of the lesson's plan, wrap and completion screens. Everything with a
// placeholder (the cue, the do-now text, the wrap lines, the next lesson) comes from the API.

/** Mirrors backend/app/domain/lessons/plans.py IF_THEN_RESPONSE_MAX (locked by planScreen.test.ts). */
export const IF_THEN_RESPONSE_MAX = 300;
/** Mirrors CONFIDENCE_MIN / CONFIDENCE_MAX in the same file. */
export const CONFIDENCE_RANGE = [1, 2, 3, 4, 5] as const;

/** What each `doNow.action` in content/lessons/*.json does in the browser (locked by the test). */
export type DoNowAction = "copy_phrase" | "print_note_template" | "print_and_copy" | "add_observation";
export const DO_NOW_ACTIONS: readonly DoNowAction[] = [
  "copy_phrase",
  "print_note_template",
  "print_and_copy",
  "add_observation",
];
export const isDoNowAction = (value: string): value is DoNowAction =>
  (DO_NOW_ACTIONS as readonly string[]).includes(value);

export const PLAN_SCREEN_COPY = {
  responseHint: "Write the words you want ready. Short is good.",
  responseAria: "Your words",
  counter: (used: number): string => `${used} of ${IF_THEN_RESPONSE_MAX}`,
  required: "Please write a few words for your plan first.",
  tooLong: `Please keep it to ${IF_THEN_RESPONSE_MAX} characters or fewer.`,
  saved: "Your plan is saved. Tap Next to finish the lesson.",
  savedPrivately: "Saved privately to this session. No account, no name needed.",
  resetPrefix: "Reset step",
  copied: "Copied",
  copyFailed: "We couldn't copy that. You can select the text and copy it yourself.",
  popupBlocked: "Your browser blocked the print window. Please allow pop-ups and try again.",
  openVisitSheet: "Open the visit sheet",
  reminderFailed: "We couldn't make the reminder file. Your plan is saved.",
  saving: "Saving...",
  printTitleSuffix: "(print)",
} as const;

export const WRAP_COPY = {
  heading: "You did it",
  finish: "Finish lesson",
  finishing: "Finishing...",
  ratingNeeded: "Please pick a number for each line, then finish.",
  scaleLow: "1 = not ready",
  scaleHigh: "5 = very ready",
  ratingOf: (n: number): string => `${n} of 5`,
  doneHeading: "Lesson complete",
  nextLabel: "Next lesson",
  opensOn: (date: string): string => `Opens ${date}`,
  backToToday: "Back to Today",
  savedPhrasesFailed: "We couldn't check your saved phrases just now.",
} as const;
