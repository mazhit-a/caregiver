import { useCallback, useEffect, useRef, useState } from "react";
import { type ApiFailure, classifyError } from "./errors";

export type RequestState<T, F = ApiFailure> =
  | { status: "loading"; data: undefined; error: undefined }
  | { status: "error"; data: undefined; error: F }
  | { status: "ready"; data: T; error: undefined };

export type Request<T, F = ApiFailure> = RequestState<T, F> & {
  /** Runs again and goes back through `loading`. */
  retry: () => void;
  /** Runs again keeping the current data on screen (no `loading`, no unmount). A failure keeps the old data. */
  refresh: () => void;
};

/**
 * Runs `fn` on mount and whenever `deps` change; `retry()` runs it again.
 * Per-component state: nothing is cached across sessions. Aborts on unmount.
 */
export function useRequest<T, F = ApiFailure>(
  fn: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
  /** Default `classifyError`; the app screens pass `classifyAppError`. */
  classify: (error: unknown) => F = classifyError as unknown as (
    error: unknown,
  ) => F,
): Request<T, F> {
  const [state, setState] = useState<RequestState<T, F>>({
    status: "loading",
    data: undefined,
    error: undefined,
  });
  const [attempt, setAttempt] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const silent = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    const quiet = silent.current;
    silent.current = false;
    if (!quiet)
      setState({ status: "loading", data: undefined, error: undefined });
    fnRef
      .current(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setState({ status: "ready", data, error: undefined });
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          const failure = classify(err);
          setState((prev) =>
            quiet && prev.status === "ready"
              ? prev
              : { status: "error", data: undefined, error: failure },
          );
        }
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const refresh = useCallback(() => {
    silent.current = true;
    setAttempt((n) => n + 1);
  }, []);
  return { ...state, retry, refresh } as Request<T, F>;
}
