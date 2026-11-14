import { useRef, useState } from "react";
import { CARE_CARD_TEXT } from "../../../content/app/careCard";
import styles from "./careCard.module.css";

/** The link lives only in this read-only input: never in the title, URL, history or console. */
export function LinkField({ link }: { link: string }) {
  const input = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState("");

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(link);
      setMessage(CARE_CARD_TEXT.linkCopied);
    } catch {
      input.current?.focus();
      input.current?.select();
      setMessage(CARE_CARD_TEXT.copyFallback);
    }
  }

  return (
    <div className={styles.section}>
      <label className={styles.linkLabel} htmlFor="care-card-link">
        {CARE_CARD_TEXT.linkLabel}
      </label>
      <div className={styles.row}>
        <input id="care-card-link" ref={input} className={styles.linkInput} readOnly value={link} />
        <button type="button" className={styles.btn} onClick={() => void copy()}>
          {CARE_CARD_TEXT.copyLink}
        </button>
      </div>
      <p className={styles.hint} role="status">
        {message}
      </p>
    </div>
  );
}
