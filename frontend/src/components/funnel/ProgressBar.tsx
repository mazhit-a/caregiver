import styles from "./ProgressBar.module.css";

interface Props {
  current: number;
  total: number;
  /** Visible and spoken text, e.g. "3 of 11" (the page supplies the wording). */
  label: string;
}

export function ProgressBar({ current, total, label }: Props) {
  return (
    <div className={styles.wrap}>
      <progress className={styles.bar} max={total} value={current} aria-label="Quiz progress" aria-valuetext={label} />
      <span className={styles.label} aria-hidden="true">
        {label}
      </span>
    </div>
  );
}
