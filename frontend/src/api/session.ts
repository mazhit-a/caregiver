import { apiRequest } from "./client";

export const TOKEN_KEY = "pcn_session_token";

let memoryToken: string | null = null;

/** Storage may throw (private mode, blocked site data): fall back to memory. */
export function getToken(): string | null {
  try {
    const stored = window.localStorage.getItem(TOKEN_KEY);
    if (stored) return stored;
  } catch {
    return memoryToken;
  }
  return memoryToken;
}

export function setToken(token: string): void {
  memoryToken = token;
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // memory only
  }
}

export function clearToken(): void {
  memoryToken = null;
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // nothing to clear
  }
}

export interface CreatedSession {
  token: string;
  timezone: string;
}

function browserTimezone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

let inFlight: Promise<CreatedSession> | null = null;

/** Single-flight: two callers at once share one POST /api/session. Stores the token. */
export function createSession(): Promise<CreatedSession> {
  if (inFlight) return inFlight;
  inFlight = apiRequest<CreatedSession>({
    method: "POST",
    path: "/session",
    body: { timezone: browserTimezone() },
    auth: false,
  })
    .then((created) => {
      setToken(created.token);
      return created;
    })
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}
