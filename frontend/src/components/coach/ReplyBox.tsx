import { useId } from "react";
import styles from "./coach.module.css";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  busy: boolean;
  max: number;
  label: string;
  hint: string;
  counter: string;
  sendLabel: string;
  busyLabel: string;
}

export function ReplyBox({ value, onChange, onSend, busy, max, label, hint, counter, sendLabel, busyLabel }: Props) {
  const id = useId();
  const canSend = value.trim() !== "" && !busy;
  return (
    <form
      className={styles["reply"]}
      onSubmit={(event) => {
        event.preventDefault();
        if (canSend) onSend();
      }}
    >
      <label htmlFor={id} className={styles["replyLabel"]}>
        {label}
      </label>
      <p className={styles["hint"]} id={`${id}-hint`}>
        {hint}
      </p>
      <textarea
        id={id}
        className={styles["textarea"]}
        value={value}
        maxLength={max}
        rows={3}
        readOnly={busy}
        aria-describedby={`${id}-hint ${id}-count`}
        onChange={(event) => onChange(event.target.value.slice(0, max))}
      />
      <div className={styles["replyFoot"]}>
        <span className={styles["count"]} id={`${id}-count`}>
          {counter}
        </span>
        <button type="submit" className={styles["primary"]} aria-disabled={!canSend}>
          {busy ? busyLabel : sendLabel}
        </button>
      </div>
    </form>
  );
}
