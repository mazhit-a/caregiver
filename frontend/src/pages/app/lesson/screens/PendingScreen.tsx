import { LESSON_COPY } from "../../../../content/app/lesson";
import styles from "./lessonScreens.module.css";

/** Stand-in for screen types whose increment (role-play G7/G8, plan and wrap G9) has not landed. */
export function PendingScreen({ title }: { title?: string }) {
  return (
    <div className={styles["screen"]}>
      {title && (
        <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
          {title}
        </h2>
      )}
      <p className={styles["body"]}>{LESSON_COPY.pendingBody}</p>
    </div>
  );
}
