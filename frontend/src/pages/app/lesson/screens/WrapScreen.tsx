import { useEffect, useState } from "react";
import { Link } from "react-router";
import { answerLesson, completeLesson, listPhrases } from "../../../../api/app";
import type { LessonComplete, WrapScreen as WrapData } from "../../../../api/appTypes";
import { useAppAction } from "../../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../../content/app/common";
import { CONFIDENCE_RANGE, WRAP_COPY as COPY } from "../../../../content/app/planScreen";
import { formatDate } from "../../../../format/date";
import { ROUTES } from "../../../../routes";
import type { ScreenProps } from "./types";
import styles from "./lessonScreens.module.css";
import wrap from "./planScreens.module.css";

export function WrapScreen({ screen, lesson }: ScreenProps<WrapData>) {
  const run = useAppAction();
  const [savedPhrase, setSavedPhrase] = useState(false);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [complete, setComplete] = useState<LessonComplete | null>(null);
  const [ratingsSent, setRatingsSent] = useState(false);
  const check = screen.confidenceCheck ?? null;

  useEffect(() => {
    const controller = new AbortController();
    void listPhrases(controller.signal)
      .then(({ phrases }) => setSavedPhrase(phrases.some((p) => p.lessonId === lesson.id)))
      .catch(() => undefined);
    return () => controller.abort();
  }, [lesson.id]);

  async function finish() {
    if (busy) return;
    if (check && check.items.some((item) => ratings[item.id] === undefined)) {
      setError(COPY.ratingNeeded);
      return;
    }
    setBusy(true);
    setError(null);
    if (check && !ratingsSent) {
      const sent = await run(() => answerLesson(lesson.id, { screenId: screen.id, value: ratings }));
      if (!sent.ok) return fail(sent);
      setRatingsSent(true);
    }
    const outcome = await run(() => completeLesson(lesson.id));
    if (!outcome.ok) return fail(outcome);
    setBusy(false);
    setComplete(outcome.data);
  }

  function fail(outcome: { ok: false; failure: { kind: keyof typeof APP_ERROR_MESSAGES }; handled: boolean }) {
    setBusy(false);
    if (!outcome.handled) setError(APP_ERROR_MESSAGES[outcome.failure.kind]);
  }

  if (complete) return <Completion data={complete} />;
  return (
    <div className={styles["screen"]}>
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {COPY.heading}
      </h2>
      <p className={styles["body"]}>{screen.skillLine}</p>
      {savedPhrase && <p className={styles["body"]}>{screen.phraseLine}</p>}
      <p className={styles["body"]}>{screen.patternLine}</p>
      {check && (
        <fieldset className={wrap["ratings"]}>
          <legend className={styles["legend"]}>{check.title}</legend>
          <p className={wrap["hint"]}>
            {check.scale}. {COPY.scaleLow}, {COPY.scaleHigh}.
          </p>
          {check.items.map((item) => (
            <fieldset key={item.id} className={wrap["item"]}>
              <legend className={wrap["itemLabel"]}>{item.label}</legend>
              <div className={wrap["scale"]}>
                {CONFIDENCE_RANGE.map((n) => (
                  <label key={n} className={wrap["rate"]}>
                    <input
                      type="radio"
                      name={`rate-${item.id}`}
                      value={n}
                      checked={ratings[item.id] === n}
                      aria-label={`${item.label}: ${COPY.ratingOf(n)}`}
                      onChange={() => setRatings((r) => ({ ...r, [item.id]: n }))}
                    />
                    <span aria-hidden="true">{n}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </fieldset>
      )}
      {error && (
        <p role="alert" className={styles["error"]}>
          {error}
        </p>
      )}
      <div className={wrap["row"]}>
        <button type="button" className={wrap["primary"]} aria-disabled={busy} onClick={() => void finish()}>
          {busy ? COPY.finishing : COPY.finish}
        </button>
      </div>
    </div>
  );
}

function Completion({ data }: { data: LessonComplete }) {
  const wrapData = data.wrap;
  return (
    <div className={styles["screen"]}>
      <h2 className={styles["title"]} data-screen-heading tabIndex={-1}>
        {COPY.doneHeading}
      </h2>
      {wrapData && <p className={styles["body"]}>{wrapData.tomorrowLine}</p>}
      {data.nextLesson ? (
        <section className={wrap["card"]} aria-label={COPY.nextLabel}>
          {wrapData && <p className={styles["body"]}>{wrapData.nextLine}</p>}
          <h3 className={wrap["cardTitle"]}>{data.nextLesson.title}</h3>
          <p className={styles["body"]}>{data.nextLesson.reason}</p>
          <p className={styles["muted"]}>{COPY.opensOn(formatDate(data.nextLesson.unlockOn))}</p>
        </section>
      ) : (
        data.allDoneLine && <p className={styles["body"]}>{data.allDoneLine}</p>
      )}
      <div className={wrap["row"]}>
        <Link to={ROUTES.today} className={wrap["primary"]}>
          {COPY.backToToday}
        </Link>
      </div>
    </div>
  );
}
