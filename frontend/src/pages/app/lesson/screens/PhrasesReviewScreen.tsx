import type { PhrasesReviewScreen as PhrasesData } from "../../../../api/appTypes";
import type { ScreenProps } from "./types";
import styles from "./lessonScreens.module.css";

export function PhrasesReviewScreen({ screen }: ScreenProps<PhrasesData>) {
  return (
    <div className={styles["screen"]}>
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {screen.title}
      </h2>
      {screen.phrases.length === 0 ? (
        <p className={styles["body"]}>{screen.emptyText}</p>
      ) : (
        <>
          <p className={styles["body"]}>{screen.intro}</p>
          <ul className={styles["list"]}>
            {screen.phrases.map((p) => (
              <li key={p.id} className={styles["phrase"]}>
                <p className={styles["phraseText"]}>{p.text}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
