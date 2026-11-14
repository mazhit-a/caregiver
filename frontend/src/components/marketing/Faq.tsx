import type { ReactNode } from "react";
import styles from "./Faq.module.css";

export interface FaqItem {
  question: string;
  answer: ReactNode;
}

interface Props {
  items: readonly FaqItem[];
}

/** Native disclosure widgets: keyboard and screen readers work without script. */
export function Faq({ items }: Props) {
  return (
    <div className={styles.faq}>
      {items.map((item) => (
        <details key={item.question} className={styles.item}>
          <summary className={styles.summary}>
            <span>{item.question}</span>
            <span className={styles.chevron} aria-hidden="true" />
          </summary>
          <div className={styles.answer}>{item.answer}</div>
        </details>
      ))}
    </div>
  );
}
