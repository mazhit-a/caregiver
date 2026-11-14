// Placeholder-free funnel strings. Mirrors content/funnel-copy.json (locked by funnel.test.ts).
// Recipient- and price-aware strings ({possessive}, prices, dates) come from GET /api/funnel-copy.
import type { ApiFailureKind } from "../api/errors";

export const COMMON = {
  notMedicalAdvice: "We teach and organize. We don't give medical advice.",
  privacyShort: "Saved privately to this session. No account, no name needed.",
  needHelpNow: "Need help now?",
  back: "Back",
  continue: "Continue",
  skip: "Skip",
} as const;

export const QUIZ_INTRO = {
  title: "Let's build your plan",
  body: "11 quick questions, about 3 minutes. Saved privately to this session. No account, no name needed.",
  cta: "Start",
} as const;

export const PLAN_PREVIEW = {
  whatWeHeardTitle: "What we heard",
  editLink: "Change my answers",
  beforeAfterTitle: "Where you'll be in 30 days",
  beforeLabel: "Today",
  afterLabel: "In 30 days",
  first30Title: "Your first 30 days",
  laterTitle: "Coming later",
  quickGuidesTitle: "Quick guides for urgent moments",
  quickGuidesNote: "Always there when you need them, outside the course.",
  reasonPrefix: "Why now: ",
} as const;

/** `{count}` filled by the caller. */
export const moduleLessonsLabel = (count: number): string => `${count} short lessons`;
export const paceLine = (perWeek: number): string =>
  `About 8 minutes a lesson, ${perWeek} lessons a week`;

export const GIFT_CARD = {
  title: "A free gift for you",
  cta: "Download free sheet",
  note: "Yours to keep, whether or not you continue.",
} as const;

export const PROOF = {
  title: "Why this works",
  // TODO(verify): confirm both statistics and sources before launch (launch checklist row).
  items: [
    {
      text: "About 1 in 4 US adults cares for a family member, and most never got any training.",
      source: "AARP and the National Alliance for Caregiving, Caregiving in the US 2025",
    },
    {
      text: "Caregiver programs that include hands-on practice, not just reading, have been shown to lower caregiver stress.",
      source: "NIH-funded REACH caregiver research",
    },
  ],
} as const;

export const DISCLAIMER = COMMON.notMedicalAdvice;

export const PAYWALL = {
  includesTitle: "What you get",
  testModeHint:
    "Test mode: use card 4242 4242 4242 4242, any future date, any CVC. No real charge.",
  demoButton: "Continue in demo mode (no charge)",
  demoNote: "For reviewers: unlocks the full demo without payment.",
  footer: "Prices in USD. We teach and organize. We don't give medical advice.",
  loading: "Opening secure checkout…",
  cardError:
    "The payment didn't go through. Please check the card details or try another card.",
} as const;

export const RESTORE_FAILED = "We couldn't restore your plan, so we started a new one.";

/** One warm, blame-free message per ApiFailure kind. "Saved" is true: answers live on the server. */
export const ERROR_MESSAGES: Record<ApiFailureKind, string> = {
  network:
    "We couldn't reach the server. Check your connection and try again. Your answers are saved privately to this session.",
  timeout: "That took longer than expected. Please try again. Your answers are saved privately to this session.",
  session_lost: RESTORE_FAILED,
  rate_limited: "Lots of requests at once. Take a breath and try again in a minute.",
  gate: "This part isn't open yet. We'll take you to the right place.",
  locked: "Your answers are already complete. We'll take you to your plan.",
  validation: "Something needs another look. Please check your answer and try again.",
  gateway: "We couldn't open checkout just now. Please try again in a moment.",
  server: "Something went wrong on our side. Please try again. Your answers are saved privately to this session.",
  unknown: "Something went wrong. Your answers are saved privately to this session. Please try again.",
};
