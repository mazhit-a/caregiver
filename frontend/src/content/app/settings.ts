// UI-owned wording for Settings and Cancel. Facts and buttons only: no offer, no survey, no
// price per day. Anything with the parent's name comes from the API (app-copy) and is not here.

export const SETTINGS = {
  title: "Settings",
  subscriptionTitle: "Subscription",
  planLabel: "Plan",
  statusLabel: "Status",
  modeLabel: "Mode",
  modeDemo: "Demo mode, no payment",
  modeStripe: "Stripe test mode",
  loading: "your subscription",
  cancelButton: "Cancel subscription",
  privacyTitle: "Privacy",
  privacyNote: "Saved privately to this session. No account, no name needed.",
  careCardLink: "Stop sharing the care card link",
  careCardHint: "You can stop sharing from the care card page.",
  retry: "Try again",
  demoDetail: "Simulated date",
  demoDone: "Done",
  demoNone: "none",
} as const;

export const STATUS_LABELS: Record<string, string> = {
  demo: "Demo",
  active: "Active",
  canceling: "Canceled, access continues",
  past_due: "Payment needed",
  canceled: "Canceled",
  ended: "Ended",
  none: "No plan",
};

/** Statuses from which the server accepts a cancel. */
export const CANCELLABLE = ["demo", "active", "past_due"] as const;

export function isCancellable(status: string): boolean {
  return (CANCELLABLE as readonly string[]).includes(status);
}

/** One honest sentence per status. `date` is already formatted for display, or null. */
export function statusText(status: string, date: string | null): string {
  switch (status) {
    case "demo":
      return date
        ? `This is a demo plan, so nothing is charged. The current period runs until ${date}.`
        : "This is a demo plan, so nothing is charged.";
    case "active":
      return date
        ? `Your plan is active. It renews on ${date} until you cancel.`
        : "Your plan is active. It renews until you cancel.";
    case "canceling":
      return date
        ? `Your plan is canceled. You keep full access until ${date}.`
        : "Your plan is canceled. You keep full access until the end of the current period.";
    case "past_due":
      return "Your last payment did not go through. You can still cancel or manage your data here.";
    case "canceled":
    case "ended":
      return "Your plan has ended.";
    default:
      return "You do not have a plan yet.";
  }
}

export const DEMO_CONTROL_LABELS: Record<string, string> = {
  nextDay: "Simulate next day (demo)",
  jumpToRenewal: "Jump to renewal (demo)",
  failNextPayment: "Fail next payment (demo, Stripe only)",
};

export const CANCEL = {
  title: "Cancel subscription",
  loading: "cancel details",
  keep: "Keep my plan",
  confirm: "Cancel anyway",
  retry: "Try again",
  back: "Back to Settings",
  doneTitle: "Your plan is canceled",
  alreadyCanceling: "Your plan is already canceled.",
  notCancellable: "There is no active plan to cancel.",
  conflict: "Your plan can't be canceled right now. It may already be canceled. Go back to Settings to check.",
  blocked: "We couldn't cancel with the payment provider, so nothing changed. Please try again.",
} as const;

const plural = (n: number, one: string, many: string): string => `${n} ${n === 1 ? one : many}`;

export interface CancelFacts {
  planName: string;
  savedPhraseCount: number;
  careCardPublished: boolean;
  /** Formatted end date, or null when the API sent none. */
  endDate: string | null;
}

/** The facts sentence(s). The access sentence is dropped when there is no end date. */
export function cancelFacts(facts: CancelFacts): string {
  const losses = [facts.planName, plural(facts.savedPhraseCount, "saved phrase", "saved phrases")];
  if (facts.careCardPublished) losses.push("your care card link");
  const list =
    losses.length > 1 ? `${losses.slice(0, -1).join(", ")} and ${losses[losses.length - 1]}` : (losses[0] ?? "");
  const lose = `${facts.endDate ? "After that you" : "You"}'ll lose access to ${list}.`;
  return facts.endDate ? `If you cancel, you keep full access until ${facts.endDate}. ${lose}` : `If you cancel, ${lose.charAt(0).toLowerCase()}${lose.slice(1)}`;
}

export function canceledText(endDate: string | null): string {
  return endDate ? `You keep full access until ${endDate}.` : "You keep full access until the end of the current period.";
}
