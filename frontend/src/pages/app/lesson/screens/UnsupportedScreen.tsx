import { LESSON_COPY } from "../../../../content/app/lesson";
import styles from "./lessonScreens.module.css";

/** A screen type this browser build does not know: calm message, the player's Next still works. */
export function UnsupportedScreen() {
  return (
    <div className={styles["screen"]}>
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {LESSON_COPY.unsupportedTitle}
      </h2>
      <p className={styles["body"]}>{LESSON_COPY.unsupportedBody}</p>
    </div>
  );
}
