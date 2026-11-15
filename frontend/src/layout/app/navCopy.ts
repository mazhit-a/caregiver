/** The slice of `GET /app-copy` the shell reads (labels are server-rendered, never filled here). */
export interface NavCopy {
  today: string;
  plan: string;
  profilePage: string;
  skills: string;
  settings: string;
}

const NAV_KEYS = [
  "today",
  "plan",
  "profilePage",
  "skills",
  "settings",
] as const;

/** The nav labels, or null when the server sent something incomplete (the shell shows its retry block). */
export function readNavCopy(nav: Partial<NavCopy> | undefined): NavCopy | null {
  return NAV_KEYS.every((key) => typeof nav?.[key] === "string")
    ? (nav as NavCopy)
    : null;
}
