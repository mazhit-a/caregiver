import type { LearnScreen as LearnData } from "../../../../api/appTypes";
import { LESSON_COPY } from "../../../../content/app/lesson";
import { OptionGroup } from "./OptionGroup";
import type { ScreenProps } from "./types";
import { useAnswer } from "./useAnswer";
import styles from "./lessonScreens.module.css";

function miniTaskResponse(entry: ScreenProps<LearnData>["entry"]): string | null {
  if (!entry) return null;
  const response = entry.result["response"];
  if (typeof response === "string" && response !== "") return response;
  const correct = entry.result["correct"];
  if (correct === true) return LESSON_COPY.miniTaskCorrect;
  if (correct === false) return LESSON_COPY.miniTaskIncorrect;
  return LESSON_COPY.miniTaskThanks;
}

export function LearnScreen({ screen, lesson, entry, remember }: ScreenProps<LearnData>) {
  const { send, busy, error } = useAnswer(lesson.id);
  const task = screen.miniTask ?? null;

  async function pick(id: string) {
    const result = await send(screen.id, id);
    if (result) remember(screen.id, (previous) => ({ value: id, result, saved: previous?.saved ?? [] }));
  }

  const feedback = miniTaskResponse(entry);
  return (
    <div className={styles["screen"]}>
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {screen.title}
      </h2>
      {screen.body && <p className={styles["body"]}>{screen.body}</p>}
      {screen.bullets && screen.bullets.length > 0 && (
        <ul className={styles["bullets"]}>
          {screen.bullets.map((b) => (
            <li key={b}>
              <span className={styles["check"]} aria-hidden="true">
                ✓
              </span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}
      {screen.extra && <p className={styles["body"]}>{screen.extra}</p>}
      {screen.patternTip && (
        <p className={styles["tip"]}>
          <span className={styles["tipLabel"]}>{LESSON_COPY.ollieTip}</span> {screen.patternTip}
        </p>
      )}
      {screen.pattern && (
        <section className={styles["pattern"]} aria-label={screen.pattern.name}>
          <h3 className={styles["patternName"]}>{screen.pattern.name}</h3>
          <ol className={styles["steps"]}>
            {screen.pattern.steps.map((s) => (
              <li key={s.id}>
                <span className={styles["stepLabel"]}>{s.label}</span>
                <span className={styles["stepExample"]}>{s.example}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
      {task && (
        <>
          <OptionGroup
            legend={task.question}
            options={task.options}
            value={entry?.value ?? null}
            disabled={busy}
            onPick={(id) => void pick(id)}
          />
          <div role="status" className={styles["feedback"]} hidden={!feedback}>
            {feedback && <p className={styles["text"]}>{feedback}</p>}
          </div>
          {error && (
            <p className={styles["error"]} role="alert">
              {error}
            </p>
          )}
        </>
      )}
    </div>
  );
}
