import { useCallback, useEffect, useRef, useState } from "react";
import { type ApiFailure, classifyError } from "../../api/errors";
import { getQuiz, putAnswer } from "../../api/funnel";
import type { AnswerValue, QuizState } from "../../api/funnelTypes";

export type QuizLoad =
  | { status: "loading" }
  | { status: "error"; failure: ApiFailure }
  | { status: "ready"; quiz: QuizState };

export interface UseQuiz {
  load: QuizLoad;
  refresh: () => void;
  /** Saves one answer, then re-fetches the quiz (server text depends on earlier answers). */
  saveAnswer: (id: string, value: AnswerValue) => Promise<{ ok: true } | { ok: false; failure: ApiFailure }>;
}

/** Holds the last GET /api/quiz for the quiz routes. Per component: nothing is cached across sessions. */
export function useQuiz(): UseQuiz {
  const [load, setLoad] = useState<QuizLoad>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    getQuiz(controller.signal)
      .then((quiz) => {
        if (!controller.signal.aborted) setLoad({ status: "ready", quiz });
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setLoad({ status: "error", failure: classifyError(err) });
      });
    return () => {
      alive.current = false;
      controller.abort();
    };
  }, [attempt]);

  const refresh = useCallback(() => {
    setLoad({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  const saveAnswer = useCallback(async (id: string, value: AnswerValue) => {
    try {
      await putAnswer(id, value);
      const quiz = await getQuiz();
      if (alive.current) setLoad({ status: "ready", quiz });
      return { ok: true } as const;
    } catch (err: unknown) {
      return { ok: false, failure: classifyError(err) } as const;
    }
  }, []);

  return { load, refresh, saveAnswer };
}
