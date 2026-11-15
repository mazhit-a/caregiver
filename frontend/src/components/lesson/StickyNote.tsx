import styles from "./lessonBlocks.module.css";

export function StickyNote({ line1, line2 }: { line1: string; line2: string }) {
  return (
    <figure className={styles["sticky"]}>
      <p className={styles["stickyLine"]}>{line1}</p>
      <p className={styles["stickyLine"]}>{line2}</p>
    </figure>
  );
}
