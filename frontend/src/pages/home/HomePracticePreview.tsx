import { useState } from "react";
import { PracticeRound } from "../../components/practice/PracticeRound";
import { HOME_PREVIEW } from "../../content/home";
import { HOME_ROUND } from "../../content/practiceScript";
import styles from "./HomePage.module.css";

/** Canned "Mom asks again" round. No network: display data only. */
export function HomePracticePreview() {
  const [picked, setPicked] = useState<number | null>(null);
  return (
    <div className={styles.preview}>
      <div className={styles.previewHead}>
        <h2 className={styles.previewTitle}>{HOME_PREVIEW.title}</h2>
        <span className={styles.badge}>{HOME_PREVIEW.badge}</span>
      </div>
      <PracticeRound
        round={HOME_ROUND}
        picked={picked}
        onPick={setPicked}
        afterFeedback={
          <button type="button" className={styles.reset} onClick={() => setPicked(null)}>
            {HOME_PREVIEW.reset}
          </button>
        }
      />
      <p className={styles.footnote}>{HOME_PREVIEW.footnote}</p>
    </div>
  );
}
