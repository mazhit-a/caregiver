// UI-owned wording for the gentle exit, clear my data and the goodbye page. Labels and facts
// only: no retention message, offer, survey or countdown. The condolence text, resources and
// the clear-data message come from the API and are not here.

export const EXIT = {
  title: "End my plan and delete my data",
  step1Heading: "What happens next",
  step1Facts: [
    "Your subscription ends now, with no further charge.",
    "Your care card link stops working.",
    "All data for this session is deleted.",
    "This cannot be undone.",
  ],
  step2Heading: "This is final",
  step2Text: "Once you continue, your plan ends and your data is deleted.",
  continue: "Continue",
  confirm: "End my plan and delete my data",
  back: "Go back",
  retry: "Try again",
  blocked:
    "We couldn't end your plan with the payment provider, so nothing was deleted and your plan is unchanged. Please try again.",
  working: "Working",
} as const;

export const CLEAR = {
  title: "Clear my data",
  intro: "Delete everything saved in this session.",
  step1Facts: [
    "Your plan, saved phrases and profile are deleted.",
    "Your care card link stops working.",
    "This cannot be undone.",
  ],
  open: "Clear my data",
  continue: "Continue",
  confirm: "Delete my data",
  back: "Go back",
  retry: "Try again",
  step2Text: "This is final. Your data will be deleted now.",
  failed: "We couldn't delete your data just now, so nothing was changed. Please try again.",
} as const;

export const GOODBYE = {
  home: "Back to the home page",
  clearedTitle: "Your data is deleted",
  resourcesFallbackHeading: "Support",
} as const;

/** Router state handed to /goodbye after a 2xx. Held in memory only; a reload shows it empty. */
export type GoodbyeState =
  | {
      kind: "exit";
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
  | { kind: "cleared"; message: string };

export function isGoodbyeState(value: unknown): value is GoodbyeState {
  if (typeof value !== "object" || value === null) return false;
  const kind = (value as { kind?: unknown }).kind;
  if (kind === "cleared") return typeof (value as { message?: unknown }).message === "string";
  if (kind === "exit") {
    const v = value as { title?: unknown; condolence?: unknown; resources?: unknown };
    return typeof v.title === "string" && typeof v.condolence === "string" && Array.isArray(v.resources);
  }
  return false;
}

/** Every string a person can read on the exit path (for the banned-phrase test). */
export function exitTexts(): string[] {
  return [
    ...Object.values(EXIT).flat(),
    ...Object.values(CLEAR).flat(),
    ...Object.values(GOODBYE),
  ];
}
