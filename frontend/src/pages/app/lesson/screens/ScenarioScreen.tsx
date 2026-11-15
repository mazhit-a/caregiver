import { useState } from "react";
import { savePhrase } from "../../../../api/app";
import type { ScenarioScreen as ScenarioData } from "../../../../api/appTypes";
import { useAppAction } from "../../../../api/useAppRequest";
import { APP_COMMON, APP_ERROR_MESSAGES } from "../../../../content/app/common";
import { LESSON_COPY } from "../../../../content/app/lesson";
import { OptionGroup } from "./OptionGroup";
import type { ScreenProps } from "./types";
import { useAnswer } from "./useAnswer";
import { useLessonCopy } from "./useAppLessonCopy";
import styles from "./lessonScreens.module.css";

const text = (value: unknown): string => (typeof value === "string" ? value : "");

export function ScenarioScreen({ screen, lesson, entry, remember }: ScreenProps<ScenarioData>) {
  const answer = useAnswer(lesson.id);
  const copy = useLessonCopy();
  const run = useAppAction();
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function pick(id: string) {
    setSaveError(null);
    const result = await answer.send(screen.id, id);
    if (result) remember(screen.id, (previous) => ({ value: id, result, saved: previous?.saved ?? [] }));
  }

  const chosen = entry ? screen.answers.find((a) => a.id === entry.value) : undefined;
  const isSaved = entry !== undefined && entry.saved.includes(entry.value);
  const canSave = entry?.result["savePhrase"] === true && chosen !== undefined;

  async function save() {
    if (!entry || !chosen || isSaved || saving) return;
    setSaving(true);
    setSaveError(null);
    const outcome = await run(() =>
      savePhrase({ text: chosen.text, source: "scenario", lessonId: lesson.id }),
    );
    setSaving(false);
    if (outcome.ok) {
      remember(screen.id, (previous) =>
        previous ? { ...previous, saved: [...previous.saved, previous.value] } : entry,
      );
    } else if (!outcome.handled) {
      const { failure } = outcome;
      setSaveError(
        failure.kind === "validation" && failure.code === "phrase_limit_reached"
          ? LESSON_COPY.phraseLimit
          : APP_ERROR_MESSAGES[failure.kind],
      );
    }
  }

  // Labels: the shared app copy (no "Wrong" anywhere); the old lessons carried their own.
  const verdictKey = entry ? text(entry.result["verdict"]) : "";
  const verdict = copy?.verdictLabels[verdictKey] ?? screen.verdictLabels?.[verdictKey];
  const afterChoice = copy?.afterChoice ?? screen.afterChoice;
  const saveLabel = copy?.saveButton ?? screen.saveButton ?? "";
  return (
    <div className={styles["screen"]}>
      {screen.intro && <p className={styles["muted"]}>{screen.intro}</p>}
      <p className={styles["body"]}>{screen.setup}</p>
      <p className={styles["bubble"]}>{screen.line}</p>
      {screen.note && <p className={styles["muted"]}>{screen.note}</p>}
      <OptionGroup
        legend={screen.question ?? screen.title ?? ""}
        options={screen.answers.map((a) => ({ id: a.id, label: a.text }))}
        value={entry?.value ?? null}
        disabled={answer.busy}
        onPick={(id) => void pick(id)}
      />
      <div role="status" className={styles["feedback"]} hidden={!entry}>
        {entry && (
          <>
            {verdict && <p className={styles["verdict"]}>{verdict}</p>}
            <p className={styles["text"]}>{text(entry.result["feedback"])}</p>
            {afterChoice && <p className={styles["muted"]}>{afterChoice}</p>}
          </>
        )}
      </div>
      {canSave && (
        <div className={styles["saveRow"]}>
          <button
            type="button"
            className={styles["secondary"]}
            aria-disabled={isSaved || saving}
            onClick={() => void save()}
          >
            {isSaved ? LESSON_COPY.saved : saving ? LESSON_COPY.saving : saveLabel}
          </button>
          {isSaved && (
            <span role="status" className={styles["muted"]}>
              {LESSON_COPY.savedNote} {APP_COMMON.privacyShort}
            </span>
          )}
        </div>
      )}
      {(answer.error || saveError) && (
        <p className={styles["error"]} role="alert">
          {answer.error ?? saveError}
        </p>
      )}
    </div>
  );
}
