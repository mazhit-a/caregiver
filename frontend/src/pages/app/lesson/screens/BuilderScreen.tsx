import { useId, useRef, useState } from "react";
import type { BuilderScreen as BuilderData } from "../../../../api/appTypes";
import { CHOICE_COPY } from "./choiceCopy";
import type { ScreenProps } from "./types";
import { useAnswer } from "./useAnswer";
import { useLessonCopy } from "./useAppLessonCopy";
import styles from "./lessonScreens.module.css";

const text = (value: unknown): string => (typeof value === "string" ? value : "");

/** Three groups, one pick each. When all three are picked the server assembles and checks the reply. */
export function BuilderScreen({ screen, lesson, entry, remember }: ScreenProps<BuilderData>) {
  const { send, error } = useAnswer(lesson.id);
  const copy = useLessonCopy();
  const name = useId();
  const latest = useRef(0);
  const [picks, setPicks] = useState<string[]>(() => (entry ? entry.value.split(",") : []));
  const [retry, setRetry] = useState<string[] | null>(null);

  async function post(next: string[]) {
    const ticket = ++latest.current;
    setRetry(null);
    const result = await send(
      screen.id,
      screen.groups.map((g) => next[screen.groups.indexOf(g)]),
    );
    if (ticket !== latest.current) return; // a newer pick superseded this one
    if (result) remember(screen.id, (previous) => ({ value: next.join(","), result, saved: previous?.saved ?? [] }));
    else setRetry(next);
  }

  function pick(groupIndex: number, optionId: string) {
    const next = screen.groups.map((_, i) => (i === groupIndex ? optionId : (picks[i] ?? "")));
    setPicks(next);
    if (next.every((p) => p !== "")) void post(next);
  }

  const result = entry?.result;
  const groups = Array.isArray(result?.["groups"]) ? (result["groups"] as { correct?: boolean }[]) : [];
  const allCorrect = result?.["allCorrect"] === true;
  const complete = picks.length === screen.groups.length && picks.every((p) => p !== "");
  return (
    <div className={styles["screen"]}>
      {screen.part && <p className={styles["part"]}>{screen.part}</p>}
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {screen.title}
      </h2>
      <p className={styles["body"]}>{screen.body}</p>
      {screen.groups.map((group, g) => {
        const verdict = entry && complete ? groups[g]?.correct : undefined;
        return (
          <fieldset key={group.id} className={styles["group"]}>
            <legend className={styles["legend"]}>
              {group.label}
              {verdict !== undefined && (
                <span className={styles["groupMark"]}>
                  <span aria-hidden="true">{verdict ? "✓ " : "• "}</span>
                  {verdict ? CHOICE_COPY.fits : CHOICE_COPY.tryAnother}
                </span>
              )}
            </legend>
            <div className={styles["chips"]}>
              {group.options.map((o) => (
                <label key={o.id} className={styles["chip"]}>
                  <input
                    type="radio"
                    className={styles["input"]}
                    name={`${name}-${group.id}`}
                    value={o.id}
                    checked={picks[g] === o.id}
                    onChange={() => pick(g, o.id)}
                  />
                  <span>{o.text}</span>
                </label>
              ))}
            </div>
          </fieldset>
        );
      })}
      <div role="status" className={styles["feedback"]} hidden={!entry || !complete}>
        {entry && complete && (
          <>
            <p className={styles["verdict"]}>{CHOICE_COPY.yourReply}</p>
            <p className={styles["reply"]}>{text(result?.["reply"])}</p>
            {copy && <p className={styles["text"]}>{allCorrect ? copy.builder.allCorrect : copy.builder.notYet}</p>}
          </>
        )}
      </div>
      {error && (
        <div className={styles["errorRow"]}>
          <p className={styles["error"]} role="alert">
            {error}
          </p>
          {retry && (
            <button type="button" className={styles["secondary"]} onClick={() => void post(retry)}>
              {CHOICE_COPY.retry}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
