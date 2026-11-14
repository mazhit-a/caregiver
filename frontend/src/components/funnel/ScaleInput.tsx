import { useId } from "react";
import styles from "./ScaleInput.module.css";

interface Props {
  legend: string;
  min: number;
  max: number;
  minLabel: string;
  maxLabel: string;
  value: number | null;
  onChange: (n: number) => void;
  error?: string;
}

export function ScaleInput({ legend, min, max, minLabel, maxLabel, value, onChange, error }: Props) {
  const name = useId();
  const endsId = `${name}-ends`;
  const numbers = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  return (
    <fieldset className={styles.group} aria-describedby={endsId}>
      <legend className={styles.legend}>{legend}</legend>
      <div className={styles.buttons}>
        {numbers.map((n) => (
          <label key={n} className={`${styles.button} ${value === n ? styles.selected : ""}`}>
            <input
              type="radio"
              className={styles.input}
              name={name}
              value={n}
              checked={value === n}
              onChange={() => onChange(n)}
            />
            <span>{n}</span>
          </label>
        ))}
      </div>
      <p id={endsId} className={styles.ends}>
        <span>
          {min} = {minLabel}
        </span>
        <span>
          {max} = {maxLabel}
        </span>
      </p>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
