import { useId, type ReactNode } from "react";
import type { PracticeRoundData } from "../../content/practiceScript";
import { FeedbackCard } from "./FeedbackCard";
import styles from "./PracticeRound.module.css";

interface Props {
  round: PracticeRoundData;
  /** Index of the chosen option, or null before a pick. Controlled by the parent. */
  picked: number | null;
  onPick: (index: number) => void;
  /** Shown under the feedback, e.g. "Try another answer" or "Next round". */
  afterFeedback?: ReactNode;
}

/** One canned round: Mom speaks, the reader picks a reply, Ollie gives feedback. No network. */
export function PracticeRound({ round, picked, onPick, afterFeedback }: Props) {
  const promptId = useId();
  const chosen = picked === null ? null : round.options[picked];
  return (
    <div className={styles.round}>
      <p className={styles.stage}>{round.stage}</p>
      <div className={styles.mom}>
        <div className={styles.avatar} aria-hidden="true">
          M
        </div>
        <p className={styles.bubble}>{round.line}</p>
      </div>
      {chosen === null ? (
        <div className={styles.options} role="group" aria-labelledby={promptId}>
          <p id={promptId} className={styles.prompt}>
            What would you say?
          </p>
          {round.options.map((option, index) => (
            <button key={option.text} type="button" className={styles.option} onClick={() => onPick(index)}>
              {option.text}
            </button>
          ))}
        </div>
      ) : null}
      <div aria-live="polite" className={styles.feedback}>
        {chosen ? (
          <>
            <div className={styles.userRow}>
              <p className={styles.user}>{chosen.text}</p>
            </div>
            <FeedbackCard option={chosen} />
            {afterFeedback}
          </>
        ) : null}
      </div>
    </div>
  );
}
