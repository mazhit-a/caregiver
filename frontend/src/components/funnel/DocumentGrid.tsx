import { useId } from "react";
import styles from "./DocumentGrid.module.css";

interface Props {
  rows: { id: string; label: string; hint: string }[];
  states: { id: string; label: string }[];
  value: Record<string, string>;
  onChange: (value: Record<string, string>) => void;
  error?: string;
}

export function DocumentGrid({ rows, states, value, onChange, error }: Props) {
  const base = useId();
  return (
    <div className={styles.grid}>
      {rows.map((row) => (
        <fieldset key={row.id} className={styles.row}>
          <legend className={styles.label}>{row.label}</legend>
          <p className={styles.hint}>{row.hint}</p>
          <div className={styles.states}>
            {states.map((s) => (
              <label key={s.id} className={`${styles.state} ${value[row.id] === s.id ? styles.selected : ""}`}>
                <input
                  type="radio"
                  className={styles.input}
                  name={`${base}-${row.id}`}
                  value={s.id}
                  checked={value[row.id] === s.id}
                  onChange={() => onChange({ ...value, [row.id]: s.id })}
                />
                <span>{s.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
