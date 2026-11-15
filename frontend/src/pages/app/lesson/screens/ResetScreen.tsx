import { useState } from "react";
import type { ResetScreen as ResetData } from "../../../../api/appTypes";
import { CHOICE_COPY } from "./choiceCopy";
import { OptionGroup } from "./OptionGroup";
import type { ScreenProps } from "./types";
import { useAnswer } from "./useAnswer";
import styles from "./lessonScreens.module.css";

/**
 * "Taking care of you": one pick, stored for the plan. The `image` pose (`ollie-calm-none`) has no
 * asset, so nothing is drawn; a mapped pose will arrive with the shared pose component.
 */
export function ResetScreen({ screen, lesson, entry, remember }: ScreenProps<ResetData>) {
  const { send, busy, error } = useAnswer(lesson.id);
  const [failedPick, setFailedPick] = useState<string | null>(null);

  async function pick(id: string) {
    setFailedPick(null);
    const result = await send(screen.id, id);
    if (result) remember(screen.id, (previous) => ({ value: id, result, saved: previous?.saved ?? [] }));
    else setFailedPick(id);
  }

  return (
    <div className={styles["screen"]}>
      {screen.part && <p className={styles["part"]}>{screen.part}</p>}
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {screen.title}
      </h2>
      <p className={styles["body"]}>{screen.body}</p>
      <OptionGroup
        legend={screen.question}
        options={screen.options}
        value={entry?.value ?? null}
        disabled={busy}
        onPick={(id) => void pick(id)}
      />
      <div role="status" className={styles["feedback"]} hidden={!entry}>
        {entry && <p className={styles["text"]}>{CHOICE_COPY.resetSaved}</p>}
      </div>
      {error && (
        <div className={styles["errorRow"]}>
          <p className={styles["error"]} role="alert">
            {error}
          </p>
          {failedPick && (
            <button type="button" className={styles["secondary"]} onClick={() => void pick(failedPick)}>
              {CHOICE_COPY.retry}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
