// Placeholder-free strings shared by every app screen. Anything with a placeholder
// ({possessive}, names, dates) comes from the API (GET /api/app-copy, finished text).
import type { AppFailure } from "../../api/errors";

export const APP_COMMON = {
  /** Mirrors content/funnel-copy.json common.privacyShort (locked by common.test.ts). */
  privacyShort: "Saved privately to this session. No account, no name needed.",
  retry: "Try again",
  save: "Save",
  cancel: "Cancel",
  copy: "Copy",
  copied: "Copied",
  loading: "Loading...",
  back: "Back",
  close: "Close",
} as const;

/** One warm, blame-free line per failure kind. Nothing here promises what the server did not do. */
export const APP_ERROR_MESSAGES: Record<AppFailure["kind"], string> = {
  network: "We couldn't reach the server. Check your connection and try again.",
  timeout: "That took longer than expected. Please try again.",
  session_lost: "Your session has ended. We'll take you back to the start.",
  rate_limited: "Lots of requests at once. Take a breath and try again in a minute.",
  gate: "This part isn't open yet. We'll take you to the right place.",
  locked: "That step is already complete.",
  validation: "Something needs another look. Please check what you entered and try again.",
  gateway: "We couldn't reach the payment provider just now. Please try again in a moment.",
  server: "Something went wrong on our side. Please try again.",
  unknown: "Something went wrong. Please try again.",
  not_found: "We can't find that. It may have been removed.",
  gone: "That is no longer available.",
  lesson_locked: "This lesson isn't open yet.",
  conflict: "That isn't possible right now. Please refresh and try again.",
  billing_failed: "We couldn't reach the payment provider, so nothing changed. Please try again.",
};
