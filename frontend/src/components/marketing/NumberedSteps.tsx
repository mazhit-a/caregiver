import type { ReactNode } from "react";
import styles from "./NumberedSteps.module.css";

export interface Step {
  title: string;
  text: ReactNode;
}

interface Props {
  steps: readonly Step[];
  /** Columns from 1280px; 1 below 768px and 2 up to 1279px for 3 or 4. */
  columns?: 1 | 2 | 3 | 4;
}

export function NumberedSteps({ steps, columns = 3 }: Props) {
  return (
    <ol className={`${styles.list} ${styles[`cols${columns}`]}`}>
      {steps.map((step, index) => (
        <li key={step.title} className={styles.item}>
          <span className={styles.badge} aria-hidden="true">
            {index + 1}
          </span>
          <h3 className={styles.title}>
            <span className={styles.visuallyHidden}>Step {index + 1}: </span>
            {step.title}
          </h3>
          <p className={styles.text}>{step.text}</p>
        </li>
      ))}
    </ol>
  );
}
