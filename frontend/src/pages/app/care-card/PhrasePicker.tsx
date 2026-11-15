import { CARE_CARD_LIMITS, CARE_CARD_TEXT } from "../../../content/app/careCard";
import styles from "./careCard.module.css";

interface Props {
  available: { id: string; text: string }[];
  chosen: string[];
  onChange: (ids: string[]) => void;
}

export function PhrasePicker({ available, chosen, onChange }: Props) {
  const full = chosen.length >= CARE_CARD_LIMITS.phrases;
  function toggle(id: string): void {
    onChange(chosen.includes(id) ? chosen.filter((x) => x !== id) : [...chosen, id]);
  }
  return (
    <fieldset className={styles.picker}>
      <legend>{CARE_CARD_TEXT.pickerTitle}</legend>
      <p className={styles.hint}>{available.length === 0 ? CARE_CARD_TEXT.pickerEmpty : CARE_CARD_TEXT.pickerHint}</p>
      {available.map((p) => {
        const checked = chosen.includes(p.id);
        return (
          <label key={p.id} className={styles.option}>
            <input type="checkbox" checked={checked} disabled={full && !checked} onChange={() => toggle(p.id)} />
            <span>{p.text}</span>
          </label>
        );
      })}
      {available.length > 0 && (
        <p className={styles.hint} role="status">
          {CARE_CARD_TEXT.pickerCount(chosen.length)}
          {full ? ` ${CARE_CARD_TEXT.pickerFull}` : ""}
        </p>
      )}
    </fieldset>
  );
}
