import { useState } from "react";
import styles from "./choice.module.css";

interface Option {
  id: string;
  label: string;
  exclusive?: boolean;
}

interface Props {
  legend: string;
  options: Option[];
  max: number;
  value: string[];
  onChange: (ids: string[]) => void;
  error?: string;
  /** Announced when the limit is reached. */
  maxMessage?: (max: number) => string;
  /** Announced when an exclusive option clears the others. */
  clearedMessage?: string;
}

export function MultiChoice({
  legend,
  options,
  max,
  value,
  onChange,
  error,
  maxMessage = (n) => `You can choose up to ${n}.`,
  clearedMessage = "Your other choices were cleared.",
}: Props) {
  const [message, setMessage] = useState("");
  const exclusiveIds = new Set(options.filter((o) => o.exclusive).map((o) => o.id));

  const toggle = (id: string) => {
    if (value.includes(id)) {
      setMessage("");
      onChange(value.filter((v) => v !== id));
      return;
    }
    if (exclusiveIds.has(id)) {
      setMessage(value.length > 0 ? clearedMessage : "");
      onChange([id]);
      return;
    }
    const rest = value.filter((v) => !exclusiveIds.has(v));
    if (rest.length >= max) {
      setMessage(maxMessage(max));
      return;
    }
    setMessage("");
    onChange([...rest, id]);
  };

  const full = value.filter((v) => !exclusiveIds.has(v)).length >= max;

  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{legend}</legend>
      {options.map((o) => {
        const checked = value.includes(o.id);
        const blocked = full && !checked && !o.exclusive;
        return (
          <label
            key={o.id}
            className={`${styles.card} ${checked ? styles.selected : ""} ${blocked ? styles.blocked : ""}`}
          >
            <input
              type="checkbox"
              className={styles.input}
              value={o.id}
              checked={checked}
              aria-disabled={blocked || undefined}
              onChange={() => toggle(o.id)}
            />
            <span className={styles.box} aria-hidden="true">
              {checked ? "✓" : ""}
            </span>
            <span>{o.label}</span>
          </label>
        );
      })}
      <p className={styles.message} role="status">
        {message}
      </p>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
