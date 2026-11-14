import styles from "./coach.module.css";

export interface SummaryLabels {
  title: string;
  bestPhraseLabel: string;
  noBestPhrase: string;
  save: string;
  saveBusy: string;
  saved: string;
  savedNote: string;
  again: string;
  continueLabel: string;
  privacy: string;
}

interface Props {
  firstVsLast: string | null;
  bestPhrase: string | null;
  labels: SummaryLabels;
  saveState: "idle" | "saving" | "saved";
  saveError: string | null;
  onSave: () => void;
  onAgain: () => void;
  onContinue: () => void;
}

export function SummaryCard({ firstVsLast, bestPhrase, labels, saveState, saveError, onSave, onAgain, onContinue }: Props) {
  return (
    <section className={styles["summary"]} aria-labelledby="coach-summary-title">
      <h2 className={styles["summaryTitle"]} id="coach-summary-title" data-screen-heading tabIndex={-1}>
        {labels.title}
      </h2>
      {firstVsLast && <p className={styles["firstLast"]}>{firstVsLast}</p>}
      <div className={styles["best"]}>
        <p className={styles["bestLabel"]}>{labels.bestPhraseLabel}</p>
        {bestPhrase ? (
          <>
            <p className={styles["bestText"]}>{bestPhrase}</p>
            <button
              type="button"
              className={styles["secondary"]}
              aria-disabled={saveState !== "idle"}
              onClick={() => saveState === "idle" && onSave()}
            >
              {saveState === "saved" ? labels.saved : saveState === "saving" ? labels.saveBusy : labels.save}
            </button>
            {saveState === "saved" && (
              <span role="status" className={styles["note"]}>
                {labels.savedNote} {labels.privacy}
              </span>
            )}
            {saveError && (
              <p role="alert" className={styles["error"]}>
                {saveError}
              </p>
            )}
          </>
        ) : (
          <p className={styles["note"]}>{labels.noBestPhrase}</p>
        )}
      </div>
      <div className={styles["actions"]}>
        <button type="button" className={styles["secondary"]} onClick={onAgain}>
          {labels.again}
        </button>
        <button type="button" className={styles["primary"]} onClick={onContinue}>
          {labels.continueLabel}
        </button>
      </div>
    </section>
  );
}
