import { useState } from "react";
import { Link } from "react-router";
import type { Phrase } from "../../../api/appTypes";
import ollieReading from "../../../assets/course/ollie-reading.webp";
import { PHRASE_SOURCE_LABEL, PROFILE_TEXT } from "../../../content/app/profile";
import { ROUTES } from "../../../routes";
import styles from "./profile.module.css";

interface Props {
  phrases: Phrase[];
  /** Server-rendered empty-state sentence. */
  emptyText: string;
  onDelete: (id: string) => Promise<boolean>;
}

function PhraseCard({ phrase, onDelete }: { phrase: Phrase; onDelete: Props["onDelete"] }) {
  const [copied, setCopied] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [failed, setFailed] = useState(false);

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(phrase.text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  async function remove(): Promise<void> {
    const ok = await onDelete(phrase.id);
    if (!ok) {
      setFailed(true);
      setConfirming(false);
    }
  }

  return (
    <li className={`${styles.card} ${styles.phraseCard}`}>
      <div className={styles.quote}>
        <span className={styles.glyph} aria-hidden="true">
          “
        </span>
        <div>
          <p>{phrase.text}</p>
          <span className={styles.source}>{PHRASE_SOURCE_LABEL[phrase.source]}</span>
        </div>
      </div>
      {confirming ? (
        <div className={styles.confirm} role="alertdialog" aria-labelledby={`del-${phrase.id}`}>
          <p id={`del-${phrase.id}`}>
            {PROFILE_TEXT.deleteTitle} {PROFILE_TEXT.deleteBody}
          </p>
          <div className={styles.row}>
            <button type="button" className={styles.btn} onClick={() => setConfirming(false)}>
              {PROFILE_TEXT.deleteKeep}
            </button>
            <button type="button" className={`${styles.btn} ${styles.danger}`} onClick={() => void remove()}>
              {PROFILE_TEXT.deleteConfirm}
            </button>
          </div>
        </div>
      ) : (
        <div className={styles.row}>
          <button type="button" className={styles.btn} onClick={() => void copy()}>
            {copied ? PROFILE_TEXT.phrasesCopied : PROFILE_TEXT.phrasesCopy}
          </button>
          <button
            type="button"
            className={styles.btn}
            aria-label={`${PROFILE_TEXT.phrasesDelete}: ${phrase.text}`}
            onClick={() => setConfirming(true)}
          >
            {PROFILE_TEXT.phrasesDelete}
          </button>
        </div>
      )}
      {failed && (
        <p className={styles.error} role="alert">
          {PROFILE_TEXT.deleteFailed}
        </p>
      )}
      <span aria-live="polite" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden" }}>
        {copied ? PROFILE_TEXT.phrasesCopied : ""}
      </span>
    </li>
  );
}

export function PhraseCards({ phrases, emptyText, onDelete }: Props) {
  if (phrases.length === 0) {
    return (
      <div className={`${styles.card} ${styles.empty}`}>
        <img src={ollieReading} alt="" width={96} height={96} />
        <div>
          <p>{emptyText}</p>
          <p style={{ marginTop: "var(--space-3)" }}>
            <Link className={styles.btn} to={ROUTES.today}>
              {PROFILE_TEXT.phrasesEmptyAction}
            </Link>
          </p>
        </div>
      </div>
    );
  }
  return (
    <ul className={styles.chips} style={{ flexDirection: "column", alignItems: "stretch" }}>
      {phrases.map((p) => (
        <PhraseCard key={p.id} phrase={p} onDelete={onDelete} />
      ))}
    </ul>
  );
}
