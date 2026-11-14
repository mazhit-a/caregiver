import { useOutletContext } from "react-router";
import type { ApiFailure } from "../../api/errors";

export interface AppContext {
  openHelp: () => void;
  /**
   * Pages report a failed app request here. 401 and 402 are handled by the shell (redirect, or the
   * past-due notice); other kinds are returned as false so the page renders its own error state.
   * `message` is the server's own text, shown in the past-due notice.
   */
  reportFailure: (failure: ApiFailure, message?: string) => boolean;
}

export function useAppContext(): AppContext {
  return useOutletContext<AppContext>();
}
