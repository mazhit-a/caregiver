import styles from "./lessonBlocks.module.css";

export function StepsList({ steps }: { steps: readonly { n: number | string; title: string; text: string }[] }) {
  return (
    <ol className={styles["stepList"]}>
      {steps.map((step) => (
        <li key={step.title} className={styles["step"]}>
          <span className={styles["badge"]} aria-hidden="true">
            {step.n}
          </span>
          <span className={styles["stepBody"]}>
            <span className={styles["itemTitle"]}>{step.title}</span>
            <span className={styles["itemText"]}>{step.text}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
