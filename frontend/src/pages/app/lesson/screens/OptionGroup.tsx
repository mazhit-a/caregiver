import { useId } from "react";
import styles from "./lessonScreens.module.css";

interface Props {
  /** Visible legend. Omit it when `labelledBy` points at the screen heading. */
  legend?: string;
  labelledBy?: string;
  options: { id: string; label: string }[];
  value: string | null;
  disabled?: boolean;
  onPick: (id: string) => void;
}

/** Native radios in a fieldset: keyboard and screen-reader friendly, one answer at a time. */
export function OptionGroup({ legend, labelledBy, options, value, disabled, onPick }: Props) {
  const name = useId();
  return (
    <fieldset className={styles["group"]} disabled={disabled} aria-labelledby={labelledBy}>
      {legend && <legend className={styles["legend"]}>{legend}</legend>}
      {options.map((o) => (
        <label key={o.id} className={styles["option"]}>
          <input
            type="radio"
            className={styles["input"]}
            name={name}
            value={o.id}
            checked={value === o.id}
            onChange={() => onPick(o.id)}
          />
          <span>{o.label}</span>
        </label>
      ))}
    </fieldset>
  );
}
