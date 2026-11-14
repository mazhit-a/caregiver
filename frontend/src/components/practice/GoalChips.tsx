import { GOAL_LABELS, type Goals } from "../../content/practiceScript";
import styles from "./GoalChips.module.css";

interface Props {
  goals: Goals;
}

/** State is in the text ("met" / "not yet"), never colour alone. */
export function GoalChips({ goals }: Props) {
  return (
    <ul className={styles.chips} aria-label="Goals">
      {GOAL_LABELS.map((label, index) => {
        const met = goals[index];
        return (
          <li key={label} className={met ? `${styles.chip} ${styles.met}` : `${styles.chip} ${styles.unmet}`}>
            <span aria-hidden="true">{met ? "✓" : "○"}</span>
            <span>{label}</span>
            <span className={styles.state}>{met ? ": met" : ": not yet"}</span>
          </li>
        );
      })}
    </ul>
  );
}
