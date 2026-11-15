import { useId } from "react";
import type { SetupQuestionScreen, SetupScreen as SetupData } from "../../../../api/appTypes";
import { OptionGroup } from "./OptionGroup";
import type { ScreenProps } from "./types";
import { useAnswer } from "./useAnswer";
import styles from "./lessonScreens.module.css";

/** `setup` (title, body, options) and the legacy `setup_question`: the pick sets the variant, then the lesson is re-fetched. */
export function SetupScreen({ screen, lesson, entry, remember, reload }: ScreenProps<SetupData | SetupQuestionScreen>) {
  const { send, busy, error } = useAnswer(lesson.id);
  const headingId = useId();
  const value = entry?.value ?? lesson.variant;

  async function pick(id: string) {
    const result = await send(screen.id, id);
    if (!result) return;
    remember(screen.id, (previous) => ({ value: id, result, saved: previous?.saved ?? [] }));
    await reload();
  }

  return (
    <div className={styles["screen"]}>
      {screen.type === "setup" ? (
        <>
          {screen.part && <p className={styles["part"]}>{screen.part}</p>}
          <h2 id={headingId} className={styles["title"]} data-screen-heading tabIndex={-1}>
            {screen.title}
          </h2>
          <p className={styles["body"]}>{screen.body}</p>
          <OptionGroup
            labelledBy={headingId}
            options={screen.options}
            value={value}
            disabled={busy}
            onPick={(id) => void pick(id)}
          />
        </>
      ) : (
        <>
          <p className={styles["speaker"]}>{screen.text}</p>
          <OptionGroup
            legend={screen.question}
            options={screen.options}
            value={value}
            disabled={busy}
            onPick={(id) => void pick(id)}
          />
        </>
      )}
      {error && (
        <p className={styles["error"]} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
