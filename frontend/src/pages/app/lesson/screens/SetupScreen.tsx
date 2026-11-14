import type { SetupQuestionScreen } from "../../../../api/appTypes";
import { OptionGroup } from "./OptionGroup";
import type { ScreenProps } from "./types";
import { useAnswer } from "./useAnswer";
import styles from "./lessonScreens.module.css";

export function SetupScreen({ screen, lesson, entry, remember, reload }: ScreenProps<SetupQuestionScreen>) {
  const { send, busy, error } = useAnswer(lesson.id);
  const value = entry?.value ?? lesson.variant;

  async function pick(id: string) {
    const result = await send(screen.id, id);
    if (!result) return;
    remember(screen.id, (previous) => ({ value: id, result, saved: previous?.saved ?? [] }));
    await reload();
  }

  return (
    <div className={styles["screen"]}>
      <p className={styles["speaker"]}>{screen.text}</p>
      <OptionGroup
        legend={screen.question}
        options={screen.options}
        value={value}
        disabled={busy}
        onPick={(id) => void pick(id)}
      />
      {error && (
        <p className={styles["error"]} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
