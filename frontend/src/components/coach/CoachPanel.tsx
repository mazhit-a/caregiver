import styles from "./coach.module.css";
import { GoalChipRow } from "./GoalChipRow";
import type { CoachView } from "./types";

export interface CoachPanelLabels {
  aiTag: string;
  goals: string;
  met: string;
  notYet: string;
  scoreLabel: string;
  score: string;
  tip: string;
  tryLabel: string;
  save: string;
  saveBusy: string;
  saved: string;
  savedNote: string;
  tryAgain: string;
}

interface Props {
  coach: CoachView;
  labels: CoachPanelLabels;
  saveState: "idle" | "saving" | "saved";
  saveError: string | null;
  onSave: () => void;
  /** Retry the current round from the start (the typed reply and this feedback are dropped). */
  onTryAgain: () => void;
}

/** Everything shown here comes from the server's verdict; nothing is scored in the browser. */
export function CoachPanel({ coach, labels, saveState, saveError, onSave, onTryAgain }: Props) {
  return (
    <section className={styles["panel"]} aria-label={labels.aiTag}>
      <div className={styles["panelHead"]}>
        <span className={styles["score"]}>
          {labels.scoreLabel}: {labels.score}
        </span>
      </div>
      <GoalChipRow goals={coach.goals} label={labels.goals} metWord={labels.met} notYetWord={labels.notYet} />
      {coach.tip && (
        <p className={styles["tip"]}>
          <strong>{labels.tip}:</strong> {coach.tip}
        </p>
      )}
      {coach.betterPhrase && (
        <div className={styles["better"]}>
          <p className={styles["betterText"]}>
            <strong>{labels.tryLabel}</strong> {coach.betterPhrase}
          </p>
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
              {labels.savedNote}
            </span>
          )}
          {saveError && (
            <p role="alert" className={styles["error"]}>
              {saveError}
            </p>
          )}
        </div>
      )}
      {coach.parentReaction && <p className={styles["reaction"]}>{coach.parentReaction}</p>}
      <div className={styles["panelFoot"]}>
        <button type="button" className={styles["secondary"]} onClick={onTryAgain}>
          {labels.tryAgain}
        </button>
        <p className={styles["aiNote"]}>{labels.aiTag}</p>
      </div>
    </section>
  );
}
