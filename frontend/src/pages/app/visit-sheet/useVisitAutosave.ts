import { useCallback, useEffect, useRef, useState } from "react";
import { putVisitSheet } from "../../../api/app";
import { useAppAction } from "../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { AUTOSAVE_MS, VISIT_VALIDATION_MESSAGES } from "../../../content/app/visit";
import { type Draft, toBody } from "./visitDraft";

export type SaveStatus =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "error"; message: string };

export interface Autosave {
  draft: Draft;
  /** Changes the draft and schedules a save after `AUTOSAVE_MS` of quiet. */
  edit: (change: (current: Draft) => Draft) => void;
  /** Saves now (blur, print, leaving). Resolves when nothing is left to send or a save failed. */
  flush: () => Promise<void>;
  status: SaveStatus;
}

/**
 * Debounced PUT of the whole sheet. Last write wins: the page's own state is the truth, a save
 * never overwrites what the user typed meanwhile, and edits made during a save go out right after.
 * A failed save keeps every word and offers a retry; a 401/402 is handed to the shell.
 */
export function useVisitAutosave(initial: Draft): Autosave {
  const run = useAppAction();
  const runRef = useRef(run);
  runRef.current = run;
  const [draft, setDraft] = useState(initial);
  const [status, setStatus] = useState<SaveStatus>({ kind: "idle" });
  const latest = useRef(initial);
  const dirty = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const running = useRef<Promise<void> | null>(null);
  const mounted = useRef(true);

  const show = useCallback((next: SaveStatus) => {
    if (mounted.current) setStatus(next);
  }, []);

  const clearTimer = (): void => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
  };

  const drain = useCallback((): Promise<void> => {
    if (running.current) return running.current;
    const job = (async () => {
      while (dirty.current) {
        dirty.current = false;
        show({ kind: "saving" });
        const result = await runRef.current(() => putVisitSheet(toBody(latest.current)));
        if (!result.ok) {
          dirty.current = true;
          const failure = result.failure;
          show(
            result.handled
              ? { kind: "idle" }
              : {
                  kind: "error",
                  message:
                    failure.kind === "validation"
                      ? (VISIT_VALIDATION_MESSAGES[failure.code] ?? APP_ERROR_MESSAGES.validation)
                      : APP_ERROR_MESSAGES[failure.kind],
                },
          );
          return;
        }
      }
      show({ kind: "saved" });
    })().finally(() => {
      running.current = null;
    });
    running.current = job;
    return job;
  }, [show]);

  const flush = useCallback((): Promise<void> => {
    clearTimer();
    return drain();
  }, [drain]);

  const edit = useCallback(
    (change: (current: Draft) => Draft) => {
      latest.current = change(latest.current);
      setDraft(latest.current);
      dirty.current = true;
      clearTimer();
      timer.current = setTimeout(() => void drain(), AUTOSAVE_MS);
    },
    [drain],
  );

  // Leaving the page sends whatever is pending (no await: the page is going away).
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      clearTimer();
      void drain();
    };
  }, [drain]);

  return { draft, edit, flush, status };
}
