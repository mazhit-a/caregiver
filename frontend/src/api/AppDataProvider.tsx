import { createContext, useContext, useMemo, type ReactNode } from "react";
import { getAppCopy } from "./app";
import type { AppCopy } from "./appTypes";
import type { AppFailure } from "./errors";
import { classifyAppError } from "./errors";
import { getToken } from "./session";
import { useRequest } from "./useRequest";

export type AppCopyState =
  | { status: "loading"; data: undefined; error: undefined; refresh: () => void }
  | { status: "error"; data: undefined; error: AppFailure; refresh: () => void }
  | { status: "ready"; data: AppCopy; error: undefined; refresh: () => void };

const AppCopyContext = createContext<AppCopyState | null>(null);

/**
 * Holds `GET /app-copy` for the signed-in session and nothing else. It is reloaded whenever the
 * session token changes or is cleared, so one session's wording never shows for another.
 */
export function AppDataProvider({ children }: { children: ReactNode }) {
  const token = getToken();
  const request = useRequest<AppCopy, AppFailure>((signal) => getAppCopy(signal), [token], classifyAppError);
  const { status, data, error, retry } = request;
  const value = useMemo(
    () => ({ status, data, error, refresh: retry }) as AppCopyState,
    [status, data, error, retry],
  );
  return <AppCopyContext.Provider value={value}>{children}</AppCopyContext.Provider>;
}

/** The finished app strings from the API. Throws outside `AppDataProvider` (a wiring bug). */
export function useAppCopy(): AppCopyState {
  const value = useContext(AppCopyContext);
  if (!value) throw new Error("useAppCopy must be used inside AppDataProvider.");
  return value;
}
