import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router";
import { answerLesson, listPhrases } from "../../../../api/app";
import type { PlanResult, PlanScreen as PlanData } from "../../../../api/appTypes";
import { useAppAction } from "../../../../api/useAppRequest";
import { APP_COMMON, APP_ERROR_MESSAGES } from "../../../../content/app/common";
import {
  IF_THEN_RESPONSE_MAX,
  PLAN_SCREEN_COPY as COPY,
  isDoNowAction,
} from "../../../../content/app/planScreen";
import { buildIcs, downloadIcs } from "../../../../lib/ics";
import { ROUTES } from "../../../../routes";
import { printNote } from "./printNote";
import type { ScreenProps } from "./types";
import styles from "./lessonScreens.module.css";
import plan from "./planScreens.module.css";

const asResult = (value: unknown): PlanResult | null =>
  typeof value === "object" && value !== null && "ifThen" in value ? (value as PlanResult) : null;

export function PlanScreen({ screen, lesson, entry, remember, answers }: ScreenProps<PlanData>) {
  const run = useAppAction();
  const roleplay = lesson.screens.find((s) => s.type === "roleplay");
  const best = roleplay ? answers?.[roleplay.id]?.result["bestPhrase"] : null;
  const [response, setResponse] = useState(
    entry?.value ?? (typeof best === "string" ? best : ""),
  );
  const touched = useRef(entry !== undefined || response !== "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const fieldId = useId();
  const result = asResult(entry?.result["plan"]);

  // Prefill from the newest phrase saved in this lesson when the run gave no best phrase.
  useEffect(() => {
    if (touched.current) return;
    const controller = new AbortController();
    void listPhrases(controller.signal)
      .then(({ phrases }) => {
        if (touched.current) return;
        const mine = phrases
          .filter((p) => p.lessonId === lesson.id)
          .sort((a, b) => b.savedAt.localeCompare(a.savedAt))[0];
        if (mine) setResponse(mine.text);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [lesson.id]);

  async function save(reminderDownloaded: boolean): Promise<PlanResult | null> {
    const text = response.trim();
    if (!text) {
      setError(COPY.required);
      return null;
    }
    if (text.length > IF_THEN_RESPONSE_MAX) {
      setError(COPY.tooLong);
      return null;
    }
    setBusy(true);
    setError(null);
    const outcome = await run(() =>
      answerLesson(lesson.id, { screenId: screen.id, value: { response: text, reminderDownloaded } }),
    );
    setBusy(false);
    if (!outcome.ok) {
      if (!outcome.handled) {
        const { failure } = outcome;
        setError(
          failure.kind === "validation" && failure.code === "invalid_screen_answer"
            ? reasonMessage(failure.details)
            : APP_ERROR_MESSAGES[failure.kind],
        );
      }
      return null;
    }
    const saved = asResult(outcome.data.result);
    remember(screen.id, () => ({
      value: text,
      result: { plan: saved },
      saved: [],
    }));
    return saved;
  }

  async function remind() {
    const saved = await save(true);
    if (!saved) return;
    try {
      downloadIcs("reminder.ics", buildIcs(saved.reminder, lesson.id));
      setNote(COPY.saved);
    } catch {
      setNote(COPY.reminderFailed);
    }
  }

  async function done() {
    if (entry) return;
    if (await save(false)) setNote(COPY.saved);
  }

  async function copyPhrase() {
    try {
      await navigator.clipboard.writeText(response.trim());
      setNote(COPY.copied);
    } catch {
      setNote(COPY.copyFailed);
    }
  }

  function printTemplate() {
    if (!printNote(screen.noteTemplate)) setNote(COPY.popupBlocked);
  }

  const action = isDoNowAction(screen.doNow.action) ? screen.doNow.action : null;
  const doNowClick = (): void => {
    if (action === "copy_phrase") void copyPhrase();
    else if (action === "print_note_template") printTemplate();
    else if (action === "print_and_copy") {
      printTemplate();
      void copyPhrase();
    }
  };

  return (
    <div className={styles["screen"]}>
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {screen.title}
      </h2>
      <p className={plan["cue"]}>{screen.ifThen.cue}</p>
      <div className={plan["field"]}>
        <label htmlFor={fieldId} className={plan["label"]}>
          {screen.ifThen.responseLabel}
        </label>
        <textarea
          id={fieldId}
          className={plan["textarea"]}
          value={response}
          readOnly={!screen.ifThen.responseEditable}
          aria-describedby={`${fieldId}-count`}
          maxLength={IF_THEN_RESPONSE_MAX + 50}
          placeholder={COPY.responseHint}
          onChange={(e) => {
            touched.current = true;
            setResponse(e.target.value);
          }}
        />
        <p id={`${fieldId}-count`} className={plan["counter"]}>
          {COPY.counter(response.length)}
        </p>
      </div>
      {result?.ifThen.reset && (
        <p className={plan["hint"]}>
          {screen.ifThen.resetLabel} {result.ifThen.reset}
        </p>
      )}
      <section className={plan["card"]} aria-labelledby={`${fieldId}-now`}>
        <h3 id={`${fieldId}-now`} className={plan["cardTitle"]}>
          {screen.doNow.title}
        </h3>
        <p className={styles["body"]}>{screen.doNow.text}</p>
        {action === "add_observation" ? (
          <Link to={ROUTES.visitSheet} className={plan["primary"]}>
            {screen.doNow.button}
          </Link>
        ) : action ? (
          <button type="button" className={plan["primary"]} onClick={doNowClick}>
            {screen.doNow.button}
          </button>
        ) : null}
      </section>
      <div className={plan["row"]}>
        <button
          type="button"
          className={styles["secondary"]}
          aria-disabled={busy}
          onClick={() => !busy && void remind()}
        >
          {screen.remindButton}
        </button>
        {!entry && (
          <button
            type="button"
            className={plan["primary"]}
            aria-disabled={busy}
            onClick={() => !busy && void done()}
          >
            {screen.doneButton}
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className={styles["error"]}>
          {error}{" "}
          <button type="button" className={styles["secondary"]} onClick={() => setError(null)}>
            {APP_COMMON.close}
          </button>
        </p>
      )}
      <p className={plan["status"]} role="status">
        {note ?? (entry ? COPY.saved : "")}
      </p>
      <p className={styles["muted"]}>{COPY.savedPrivately}</p>
    </div>
  );
}

function reasonMessage(details: unknown): string {
  const reason =
    typeof details === "object" && details !== null && "reason" in details
      ? String((details as { reason: unknown }).reason)
      : "";
  if (reason === "response_too_long") return COPY.tooLong;
  if (reason === "response_required") return COPY.required;
  return APP_ERROR_MESSAGES.validation;
}
