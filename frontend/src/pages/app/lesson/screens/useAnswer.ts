import { useState } from "react";
import { answerLesson } from "../../../../api/app";
import { useAppAction } from "../../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../../content/app/common";

/** Posts one answer; keeps the failure text for the screen's own alert. */
export function useAnswer(lessonId: string) {
  const run = useAppAction();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(screenId: string, value: unknown): Promise<Record<string, unknown> | null> {
    setBusy(true);
    setError(null);
    const outcome = await run(() => answerLesson(lessonId, { screenId, value }));
    setBusy(false);
    if (outcome.ok) return outcome.data.result;
    if (!outcome.handled) setError(APP_ERROR_MESSAGES[outcome.failure.kind]);
    return null;
  }
  return { send, busy, error };
}
