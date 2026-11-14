import avatar from "../../assets/ollie-avatar.png";
import { scoreOf, type PracticeOption } from "../../content/practiceScript";
import { GoalChips } from "./GoalChips";
import styles from "./FeedbackCard.module.css";

interface Props {
  option: Pick<PracticeOption, "goals" | "tip" | "mom">;
}

export function FeedbackCard({ option }: Props) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <img src={avatar} alt="" width={36} height={36} className={styles.avatar} />
        <span className={styles.name}>Ollie’s feedback</span>
        <span className={styles.score}>{scoreOf(option)} of 3</span>
      </div>
      <GoalChips goals={option.goals} />
      <p className={styles.tip}>{option.tip}</p>
      <div className={styles.mom}>
        <p className={styles.momLabel}>Mom</p>
        <p className={styles.momText}>{option.mom}</p>
      </div>
    </div>
  );
}
