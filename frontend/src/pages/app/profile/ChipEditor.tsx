import { useId, useState } from "react";
import { PROFILE_LIMITS, PROFILE_TEXT } from "../../../content/app/profile";
import styles from "./profile.module.css";

interface Props {
  /** Server-rendered group title ("Enjoys"). */
  title: string;
  items: string[];
  onChange: (items: string[]) => void;
}

/** A list of short chips: type and press Enter (or Add); every chip has a labelled remove button. */
export function ChipEditor({ title, items, onChange }: Props) {
  const id = useId();
  const [text, setText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const full = items.length >= PROFILE_LIMITS.listItems;

  function add(): void {
    const value = text.split(/\s+/).filter(Boolean).join(" ");
    if (!value) return;
    if (value.length > PROFILE_LIMITS.itemLength) {
      setMessage(PROFILE_TEXT.chipTooLong);
      return;
    }
    if (full) {
      setMessage(PROFILE_TEXT.chipsFull);
      return;
    }
    setMessage(null);
    onChange([...items, value]);
    setText("");
  }

  return (
    <fieldset className={styles.field} style={{ border: 0, padding: 0, margin: 0 }}>
      <legend>{title}</legend>
      {items.length > 0 && (
        <ul className={styles.chips} aria-label={title}>
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className={styles.chip}>
              {item}
              <button
                type="button"
                className={styles.chipRemove}
                aria-label={`${PROFILE_TEXT.removeChip} ${item} from ${title}`}
                onClick={() => onChange(items.filter((_, i) => i !== index))}
              >
                <span aria-hidden="true">×</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className={styles.addRow}>
        <label htmlFor={id} style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clipPath: "inset(50%)" }}>
          {`${PROFILE_TEXT.addChip} to ${title}`}
        </label>
        <input
          id={id}
          className={styles.input}
          type="text"
          value={text}
          maxLength={PROFILE_LIMITS.itemLength + 20}
          placeholder={PROFILE_TEXT.chipPlaceholder}
          onChange={(event) => {
            setText(event.target.value);
            setMessage(null);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              add();
            }
          }}
        />
        <button type="button" className={styles.btn} onClick={add} aria-label={`${title}: ${PROFILE_TEXT.addChip}`}>
          {PROFILE_TEXT.addChip}
        </button>
      </div>
      {message && (
        <p className={styles.fieldError} role="alert">
          {message}
        </p>
      )}
    </fieldset>
  );
}
