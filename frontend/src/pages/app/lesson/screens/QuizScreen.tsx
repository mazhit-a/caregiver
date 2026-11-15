import { useId, useState } from "react";
import type { QuizScreen as QuizData } from "../../../../api/appTypes";
import { CHOICE_COPY } from "./choiceCopy";
import type { ScreenProps } from "./types";
import { useAnswer } from "./useAnswer";
import { useLessonCopy } from "./useAppLessonCopy";
import styles from "./lessonScreens.module.css";

const text = (value: unknown): string => (typeof value === "string" ? value : "");

/** One question, native radios. The server says what is right; the first pick locks the screen. */
export function QuizScreen({ screen, lesson, entry, remember }: ScreenProps<QuizData>) {
  const { send, busy, error } = useAnswer(lesson.id);
  const copy = useLessonCopy();
  const name = useId();
  const headingId = useId();
  const [failedPick, setFailedPick] = useState<string | null>(null);

  async function pick(id: string) {
    setFailedPick(null);
    const result = await send(screen.id, id);
    if (result) remember(screen.id, (previous) => ({ value: id, result, saved: previous?.saved ?? [] }));
    else setFailedPick(id);
  }

  const result = entry?.result;
  const correct = result?.["correct"] === true;
  const rightId = text(result?.["correctOptionId"]);
  const locked = entry !== undefined;
  return (
    <div className={styles["screen"]}>
      {screen.part && <p className={styles["part"]}>{screen.part}</p>}
      <h2 id={headingId} className={styles["title"]} data-screen-heading tabIndex={-1}>
        {screen.title}
      </h2>
      <fieldset className={styles["group"]} disabled={busy || locked} aria-labelledby={headingId}>
        {screen.options.map((o) => {
          const picked = entry?.value === o.id;
          const state = locked && o.id === rightId ? "right" : locked && picked ? "wrong" : "idle";
          return (
            <label key={o.id} className={styles["option"]} data-state={state}>
              <input
                type="radio"
                className={styles["input"]}
                name={name}
                value={o.id}
                checked={picked}
                onChange={() => void pick(o.id)}
              />
              <span className={styles["optionText"]}>{o.text}</span>
              {state === "right" && (
                <span className={styles["mark"]}>
                  <span aria-hidden="true">✓ </span>
                  {CHOICE_COPY.correct}
                </span>
              )}
              {state === "wrong" && (
                <span className={styles["mark"]}>
                  <span aria-hidden="true">• </span>
                  {CHOICE_COPY.notQuite}
                </span>
              )}
            </label>
          );
        })}
      </fieldset>
      <div role="status" className={styles["feedback"]} hidden={!entry}>
        {entry && (
          <>
            {copy && <p className={styles["verdict"]}>{correct ? copy.quiz.right : copy.quiz.wrong}</p>}
            <p className={styles["text"]}>{text(result?.["feedback"])}</p>
          </>
        )}
      </div>
      {error && (
        <div className={styles["errorRow"]}>
          <p className={styles["error"]} role="alert">
            {error}
          </p>
          {failedPick && (
            <button type="button" className={styles["secondary"]} onClick={() => void pick(failedPick)}>
              {CHOICE_COPY.retry}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
