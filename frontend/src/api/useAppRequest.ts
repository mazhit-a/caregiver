import { useEffect, useRef } from "react";
import { useOutletContext } from "react-router";
import type { AppContext } from "../layout/app/appContext";
import { ApiError } from "./client";
import { type AppFailure, classifyAppError, isShellFailure } from "./errors";
import { type Request, useRequest } from "./useRequest";

export type AppRequest<T> = Request<T, AppFailure> & {
  /** True when the app shell took over (401 redirect, 402 redirect or the past-due notice). */
  handled: boolean;
};

type ReportFailure = AppContext["reportFailure"];

/** The shell's context; undefined outside an `Outlet` (public pages, isolated tests). */
function useReportFailure(): ReportFailure | undefined {
  const context = useOutletContext<AppContext | null | undefined>();
  return context?.reportFailure;
}

/**
 * `useRequest` plus the app gate rules, in one place. A 401 or 402 is reported to the shell
 * (`AppLayout`), which redirects or renders the past-due notice; the page then renders nothing
 * for that failure (`handled`). Everything else (429, 5xx, network, timeout, 404, 423 ...) is
 * returned as `error` for the page's own retry block. Outside the shell nothing is handled.
 */
export function useAppRequest<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
): AppRequest<T> {
  const report = useReportFailure();
  const message = useRef<string | undefined>(undefined);
  const request = useRequest<T, AppFailure>(
    async (signal) => {
      try {
        return await fn(signal);
      } catch (error) {
        message.current = error instanceof ApiError ? error.message : undefined;
        throw error;
      }
    },
    deps,
    classifyAppError,
  );
  const error = request.status === "error" ? request.error : undefined;
  useEffect(() => {
    if (error && isShellFailure(error)) report?.(error, message.current);
  }, [error, report]);
  const handled = error !== undefined && isShellFailure(error) && report !== undefined;
  return { ...request, handled } as AppRequest<T>;
}

export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; failure: AppFailure; handled: boolean };

/**
 * Runs a mutation. Same gate rules as `useAppRequest`: a 401 or 402 goes to the shell
 * (`report`) and comes back `handled`; other failures are returned for the caller to show.
 */
export async function runAppAction<T>(
  action: () => Promise<T>,
  report?: ReportFailure,
): Promise<ActionResult<T>> {
  try {
    return { ok: true, data: await action() };
  } catch (error) {
    const failure = classifyAppError(error);
    const message = error instanceof ApiError ? error.message : undefined;
    const handled = report !== undefined && isShellFailure(failure) ? report(failure, message) : false;
    return { ok: false, failure, handled };
  }
}

/** `runAppAction` bound to the shell's `reportFailure`. */
export function useAppAction(): <T>(action: () => Promise<T>) => Promise<ActionResult<T>> {
  const report = useReportFailure();
  return (action) => runAppAction(action, report);
}
