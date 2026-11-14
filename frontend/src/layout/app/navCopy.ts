import { apiRequest } from "../../api/client";
import { type Request, useRequest } from "../../api/useRequest";

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

interface AppCopyNav {
  nav: NavCopy;
}

/** Local, type-only view of app-copy; G1's AppDataProvider replaces the fetch later. */
export function useNavCopy(): Request<NavCopy> {
  const state = useRequest<AppCopyNav>(
    (signal) =>
      apiRequest<AppCopyNav>({
        method: "GET",
        path: "/app-copy",
        signal,
        auth: true,
      }),
    [],
  );
  if (state.status === "ready") {
    const nav = state.data.nav as Partial<NavCopy> | undefined;
    const valid = NAV_KEYS.every((key) => typeof nav?.[key] === "string");
    if (!valid) {
      return {
        status: "error",
        data: undefined,
        error: { kind: "unknown" },
        retry: state.retry,
      };
    }
    return { ...state, data: state.data.nav } as Request<NavCopy>;
  }
  return state as Request<NavCopy>;
}
