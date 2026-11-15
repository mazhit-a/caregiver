// UI-owned strings for the demo controls. The label and the control labels come from the API
// (content/funnel-copy.json today.demo); nothing here has a placeholder.
export const DEMO = {
  appDateLabel: "Simulated date",
  movedForward: "Day moved forward",
  renewalJumped: "Jumped to the renewal date",
  syncing: "Syncing with the Stripe test clock",
  syncStalled: "Still syncing with the Stripe test clock. It can take a little longer.",
  syncDone: "Stripe test clock is in sync",
  retry: "Try again",
  working: "Working",
} as const;

/** What the status region says after each control (ids are the API's control ids). */
export const DEMO_DONE_TEXT: Record<string, string> = {
  nextDay: DEMO.movedForward,
  jumpToRenewal: DEMO.renewalJumped,
};

export const SYNC_POLL_MS = 2000;
export const SYNC_MAX_POLLS = 15;
