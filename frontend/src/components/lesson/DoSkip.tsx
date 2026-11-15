import styles from "./lessonBlocks.module.css";

interface Props {
  doItems: readonly string[];
  skipItems: readonly string[];
  doLabel: string;
  skipLabel: string;
}

/** Two boxes. The heading words carry the meaning; the marks are decoration, so colour is never the only cue. */
export function DoSkip({ doItems, skipItems, doLabel, skipLabel }: Props) {
  return (
    <div className={styles["doSkip"]}>
      <section className={`${styles["box"]} ${styles["boxDo"]}`} aria-label={doLabel}>
        <h3 className={styles["boxTitle"]}>
          <span aria-hidden="true">✓ </span>
          {doLabel}
        </h3>
        <ul className={styles["boxList"]}>
          {doItems.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </section>
      <section className={`${styles["box"]} ${styles["boxSkip"]}`} aria-label={skipLabel}>
        <h3 className={styles["boxTitle"]}>
          <span aria-hidden="true">✕ </span>
          {skipLabel}
        </h3>
        <ul className={styles["boxList"]}>
          {skipItems.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
