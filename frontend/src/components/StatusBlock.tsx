import type { ReactNode } from "react";
import styles from "./StatusBlock.module.css";

interface Props {
  status: "loading" | "error";
  /** What is loading, e.g. "prices". Used in the accessible text. */
  what: string;
  onRetry: () => void;
  children?: ReactNode;
}

export function StatusBlock({ status, what, onRetry, children }: Props) {
  if (status === "loading") {
    return (
      <div className={styles.skeleton} aria-busy="true" role="status">
        <span className={styles.visuallyHidden}>Loading {what}</span>
        {children}
      </div>
    );
  }
  return (
    <div className={styles.error} role="alert">
      <p>We could not load the {what}.</p>
      <button type="button" className={styles.retry} onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
