import type { CrisisResource } from "./types";

/**
 * Used only when the crisis request fails, so help is never blank.
 * A contract test compares these numbers with content/crisis-resources.json.
 */
export const CRISIS_FALLBACK: readonly CrisisResource[] = [
  {
    id: "emergency_911",
    name: "Emergency services",
    phone: "911",
    description: "If this is happening now, call 911.",
  },
  {
    id: "lifeline_988",
    name: "988 Suicide & Crisis Lifeline",
    phone: "988",
    description: "Call or text 988, any time, for you or someone you care about.",
  },
  {
    id: "alz_helpline",
    name: "Alzheimer's Association 24/7 Helpline",
    phone: "1-800-272-3900",
    description: "Free support and advice from trained staff, day or night.",
  },
];
