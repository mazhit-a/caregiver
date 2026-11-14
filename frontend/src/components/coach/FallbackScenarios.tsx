import { useState } from "react";
import styles from "./coach.module.css";

export interface FallbackScenarioView {
  id: string;
  setup: string;
  line: string;
  answers: { text: string; verdict: string; feedback: string }[];
}

export interface FallbackLabels {
  aiDown: string;
  intro: string;
  progress: (n: number, total: number) => string;
  verdicts: Record<string, string>;
  next: string;
  finish: string;
  finishing: string;
  skip: string;
}

interface Props {
  scenarios: FallbackScenarioView[];
  labels: FallbackLabels;
  finishing: boolean;
  finishError: string | null;
  onFinish: () => void;
  onSkip: () => void;
}

/** Multiple-choice practice shown when the AI partner is unavailable. Wording comes from the API. */
export function FallbackScenarios({ scenarios, labels, finishing, finishError, onFinish, onSkip }: Props) {
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const scenario = scenarios[index];
  if (!scenario) return null;
  const last = index >= scenarios.length - 1;
  const chosen = picked === null ? undefined : scenario.answers[picked];

  return (
    <section className={styles["fallback"]} aria-label={labels.progress(index + 1, scenarios.length)}>
      <p className={styles["note"]} role="status">
        {labels.aiDown}
      </p>
      <p className={styles["note"]}>
        {labels.progress(index + 1, scenarios.length)}. {labels.intro}
      </p>
      <p className={styles["stage"]}>{scenario.setup}</p>
      <p className={styles["parentBubble"]}>{scenario.line}</p>
      <ul className={styles["choices"]}>
        {scenario.answers.map((answer, i) => (
          <li key={answer.text}>
            <button
              type="button"
              className={styles["choice"]}
              aria-pressed={picked === i}
              onClick={() => setPicked(i)}
            >
              {answer.text}
            </button>
          </li>
        ))}
      </ul>
      {chosen && (
        <p className={styles["feedback"]} role="status">
          <strong>{labels.verdicts[chosen.verdict] ?? ""}</strong> {chosen.feedback}
        </p>
      )}
      {finishError && (
        <p className={styles["error"]} role="alert">
          {finishError}
        </p>
      )}
      <div className={styles["actions"]}>
        {chosen &&
          (last ? (
            <button type="button" className={styles["primary"]} aria-disabled={finishing} onClick={() => !finishing && onFinish()}>
              {finishing ? labels.finishing : labels.finish}
            </button>
          ) : (
            <button
              type="button"
              className={styles["primary"]}
              onClick={() => {
                setIndex(index + 1);
                setPicked(null);
              }}
            >
              {labels.next}
            </button>
          ))}
        <button type="button" className={styles["secondary"]} onClick={onSkip}>
          {labels.skip}
        </button>
      </div>
    </section>
  );
}
