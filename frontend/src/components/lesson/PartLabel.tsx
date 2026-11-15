import styles from "./lessonBlocks.module.css";

/** The small label above a screen title (the lesson part). Nothing when the screen has none. */
export function PartLabel({ part }: { part: string | null | undefined }) {
  if (!part) return null;
  return <p className={styles["part"]}>{part}</p>;
}
