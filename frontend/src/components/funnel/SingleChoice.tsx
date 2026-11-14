import { useId } from "react";
import styles from "./choice.module.css";

interface Option {
  id: string;
  label: string;
  exclusive?: boolean;
}

interface Props {
  legend: string;
  options: Option[];
  value: string | null;
  onChange: (id: string) => void;
  error?: string;
}

export function SingleChoice({ legend, options, value, onChange, error }: Props) {
  const name = useId();
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{legend}</legend>
      {options.map((o) => (
        <label key={o.id} className={`${styles.card} ${value === o.id ? styles.selected : ""}`}>
          <input
            type="radio"
            className={styles.input}
            name={name}
            value={o.id}
            checked={value === o.id}
            onChange={() => onChange(o.id)}
          />
          <span>{o.label}</span>
        </label>
      ))}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
