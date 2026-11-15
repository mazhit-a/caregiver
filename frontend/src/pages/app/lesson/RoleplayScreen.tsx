import { useState } from "react";
import type { RoleplayFinish, RoleplayScreen as RoleplayData } from "../../../api/appTypes";
import { GoalChipRow } from "../../../components/coach/GoalChipRow";
import { COACH_COPY } from "../../../content/app/coach";
import { RoleplayRoom } from "../roleplay/RoleplayRoom";
import type { AnswerEntry, ScreenProps } from "./screens/types";
import styles from "./screens/lessonScreens.module.css";

/** Registry entry: intro, goals and labels, then the room once the learner starts. */
const entry = (finish: RoleplayFinish | null): AnswerEntry => ({
  value: finish?.bestPhrase ?? "",
  result: { bestPhrase: finish?.bestPhrase ?? null },
  saved: [] as never[],
});

export function RoleplayScreen({ screen, lesson, remember }: ScreenProps<RoleplayData>) {
  const [started, setStarted] = useState(false);
  return (
    <div className={styles["screen"]}>
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {screen.title}
      </h2>
      {!started ? (
        <>
          <p className={styles["body"]}>{screen.intro}</p>
          <GoalChipRow
            label={COACH_COPY.goalsLabel}
            metWord={COACH_COPY.goalMet}
            notYetWord={COACH_COPY.goalNotYet}
            goals={screen.goals.map((key) => ({
              key,
              label: COACH_COPY.goalLabels[key] ?? key,
              met: false,
            }))}
          />
          <p className={styles["muted"]}>{screen.labels.partner}</p>
          <p className={styles["muted"]}>{screen.labels.notSaved}</p>
          <button type="button" className={styles["secondary"]} onClick={() => setStarted(true)}>
            {COACH_COPY.startButton}
          </button>
        </>
      ) : (
        <RoleplayRoom
          lessonId={lesson.id}
          context="lesson"
          summaryText={screen.summary}
          onDone={(finish) => remember(screen.id, () => entry(finish))}
          onSummary={(finish) => remember(screen.id, () => entry(finish))}
        />
      )}
    </div>
  );
}
