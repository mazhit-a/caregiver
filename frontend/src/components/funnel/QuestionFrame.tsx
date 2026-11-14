import type { ReactNode } from "react";
import styles from "./QuestionFrame.module.css";

interface Props {
  title: string;
  subtitle?: string;
  /** Privacy note shown only for health questions (text comes from the page). */
  healthNote?: string;
  children: ReactNode;
}

export function QuestionFrame({ title, subtitle, healthNote, children }: Props) {
  return (
    <div className={styles.frame}>
      <h1 className={styles.title} data-funnel-heading tabIndex={-1}>
        {title}
      </h1>
      {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      {children}
      {healthNote && <p className={styles.note}>{healthNote}</p>}
    </div>
  );
}
