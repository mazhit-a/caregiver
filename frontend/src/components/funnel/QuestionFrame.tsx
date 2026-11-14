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
      <div className={styles.head}>
        <h1 className={styles.title} data-funnel-heading tabIndex={-1}>
          {title}
        </h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
      {children}
      {healthNote && (
        <p className={styles.note}>
          <svg
            className={styles.lock}
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
          </svg>
          <span>{healthNote}</span>
        </p>
      )}
    </div>
  );
}
