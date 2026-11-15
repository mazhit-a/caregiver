import styles from "./lessonBlocks.module.css";

export function KeyIdea({ text }: { text: string }) {
  return <p className={styles["keyIdea"]}>{text}</p>;
}
