import styles from "./coach.module.css";

interface Props {
  stage?: string;
  line: string;
}

/** The practice partner's line, with the scene-setting sentence above it. */
export function ParentBubble({ stage, line }: Props) {
  return (
    <div className={styles["parent"]}>
      {stage && <p className={styles["stage"]}>{stage}</p>}
      <p className={styles["parentBubble"]}>{line}</p>
    </div>
  );
}
