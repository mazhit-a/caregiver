import styles from "./coach.module.css";
import type { GoalState } from "./types";

interface Props {
  goals: GoalState[];
  label: string;
  metWord: string;
  notYetWord: string;
}

/** State is in the words and the mark, never colour alone. */
export function GoalChipRow({ goals, label, metWord, notYetWord }: Props) {
  return (
    <ul className={styles["chips"]} aria-label={label}>
      {goals.map((goal) => (
        <li key={goal.key} className={`${styles["chip"]} ${goal.met ? styles["met"] : styles["unmet"]}`}>
          <span aria-hidden="true">{goal.met ? "✓" : "○"}</span>
          <span>{goal.label}</span>
          <span className={styles["srOnly"]}>: {goal.met ? metWord : notYetWord}</span>
        </li>
      ))}
    </ul>
  );
}
