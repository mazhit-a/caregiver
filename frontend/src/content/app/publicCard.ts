// Static strings of the public care card page (`/card/:cardId`). No placeholders: the only text built
// from user data is the page title (see `cardTitle`), which is limited to the two fields below.
import { NOT_MEDICAL_ADVICE } from "../../layout/nav";

export const PUBLIC_CARD = {
  disclaimer: NOT_MEDICAL_ADVICE,
  loading: "Loading the care card",
  sections: {
    enjoys: "Enjoys",
    calms: "Calms",
    avoid: "Try to avoid",
    rhythm: "Daily rhythm",
    phrases: "Phrases that work",
    contacts: "Contacts",
    helplines: "Helplines",
  },
  notFound: {
    title: "We can't find this card",
    body: "Check the link and try again.",
  },
  revoked: {
    title: "This card is no longer shared",
    body: "The person who shared it has turned the link off.",
  },
  rateLimited: {
    title: "Too many people opened this link",
    body: "Try again in a minute.",
  },
  failed: {
    title: "We couldn't load this card",
    body: "Check your connection and try again.",
  },
  retry: "Try again",
  print: "Print this card",
  logoLink: "Kelper home",
} as const;

/** The single client-side interpolation: "What works with {displayName}". Never includes the card id. */
export function cardTitle(displayName: string | null): string {
  return displayName ? `What works with ${displayName}` : "Care card";
}

export const sharedBy = (caregiverFirstName: string): string => `Shared by ${caregiverFirstName}`;
export const updatedOn = (formatted: string): string => `Updated ${formatted}`;
