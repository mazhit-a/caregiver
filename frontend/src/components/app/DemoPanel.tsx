import type { ReactNode } from "react";
import styles from "./DemoPanel.module.css";

export interface DemoControl {
  id: string;
  label: string;
}

interface Props {
  /** The server label, always visible. */
  label: string;
  controls: readonly DemoControl[];
  /** Id of the control being processed, or null. All buttons are disabled while one runs. */
  busyId: string | null;
  /** Polite status line ("Day moved forward", "Syncing ..."). */
  status: string | null;
  /** Inline failure with a retry. */
  error: string | null;
  retryLabel: string;
  /** Extra line, e.g. the simulated date. */
  detail?: ReactNode;
  onPress: (id: string) => void;
  onRetry: () => void;
}

/** Presentational: dashed demo block with labelled controls. No fetching, no copy of its own. */
export function DemoPanel({
  label,
  controls,
  busyId,
  status,
  error,
  retryLabel,
  detail,
  onPress,
  onRetry,
}: Props) {
  const busy = busyId !== null;
  return (
    <section className={styles.panel} aria-label={label}>
      <p className={styles.label}>{label}</p>
      {detail && <p className={styles.detail}>{detail}</p>}
      <div className={styles.controls}>
        {controls.map((control) => (
          <button
            key={control.id}
            type="button"
            className={styles.button}
            disabled={busy}
            aria-busy={busyId === control.id}
            onClick={() => onPress(control.id)}
          >
            {control.label}
          </button>
        ))}
      </div>
      <p className={styles.status} role="status">
        {status}
      </p>
      {error && (
        <div className={styles.error} role="alert">
          <p>{error}</p>
          <button type="button" className={styles.retry} disabled={busy} onClick={onRetry}>
            {retryLabel}
          </button>
        </div>
      )}
    </section>
  );
}
