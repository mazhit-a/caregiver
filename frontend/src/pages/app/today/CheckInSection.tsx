import { useRef, useState } from "react";
import { submitCheckin } from "../../../api/app";
import type { CheckinBody, CheckinResult, Today } from "../../../api/appTypes";
import { useAppAction } from "../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { CHECKIN } from "../../../content/app/checkin";
import { useTodayRefresh } from "./refresh";
import styles from "./checkin.module.css";

type Card = NonNullable<Today["checkIn"]>;
type Choice = Card["options"][number];

/** The user's own plan, quoted back. Never a fixed example. */
function PlanQuote({ plan }: { plan: Card["plan"] }) {
  return (
    <blockquote className={styles.quote}>
      <p className={styles.quoteLabel}>{CHECKIN.yourPlan}</p>
      <p className={styles.quoteText}>
        {plan.cue} {plan.response}
      </p>
    </blockquote>
  );
}

function Result({ result }: { result: CheckinResult }) {
  return (
    <div className={styles.result}>
      {result.responseText && <p className={styles.reply}>{result.responseText}</p>}
      {result.followUps.length > 0 && (
        <>
          <h3 className={styles.listTitle}>{CHECKIN.followUpsHeading}</h3>
          <ul className={styles.followUps}>
            {result.followUps.map((f) => (
              <li key={f.title}>
                <strong>{f.title}</strong>
                <p className={styles.body}>{f.text}</p>
              </li>
            ))}
          </ul>
        </>
      )}
      {result.observationAdded && <p className={styles.ack}>{CHECKIN.addedToSheet}</p>}
      {result.taskDone && <p className={styles.ack}>{CHECKIN.taskDone}</p>}
    </div>
  );
}

/** Return-visit check-in: answer, optional follow-up, then POST /checkins. Shows the server's reply. */
export function CheckInSection({ today }: { today: Today }) {
  const card = today.checkIn;
  const runAction = useAppAction();
  const refreshToday = useTodayRefresh();
  const [cameUp, setCameUp] = useState<string | null>(null);
  const [noteOn, setNoteOn] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answered, setAnswered] = useState(false);
  const [result, setResult] = useState<CheckinResult | null>(null);
  const sending = useRef(false);

  if (!card) return null;

  const followUp = card.followUp;
  const needsOutcome = followUp !== null && cameUp !== null && followUp.ifAnswer === cameUp;
  const offersNote = followUp !== null;

  async function send(came: string, outcome?: Choice["id"]) {
    if (!card || sending.current) return;
    sending.current = true;
    setBusy(true);
    setError(null);
    const body: CheckinBody = { planId: card.planId, cameUp: came };
    if (outcome) body.outcome = outcome as NonNullable<CheckinBody["outcome"]>;
    if (offersNote && noteOn) {
      const text = noteText.trim();
      body.doctorNote = text ? { addToVisitSheet: true, text } : { addToVisitSheet: true };
    }
    const res = await runAction(() => submitCheckin(body));
    sending.current = false;
    setBusy(false);
    if (res.ok) {
      setResult(res.data);
      return;
    }
    if (res.handled) return;
    if (res.failure.kind === "conflict" && res.failure.code === "checkin_already_answered") {
      setAnswered(true);
      refreshToday();
      return;
    }
    setError(APP_ERROR_MESSAGES[res.failure.kind]);
  }

  function pickFirst(id: string) {
    if (followUp && followUp.ifAnswer === id) {
      setCameUp(id);
      return;
    }
    setCameUp(id);
    void send(id);
  }

  const heading = (
    <h2 id="today-checkin" className={styles.title}>
      {CHECKIN.heading}
    </h2>
  );

  if (answered) {
    return (
      <section className={styles.card} aria-labelledby="today-checkin">
        {heading}
        <p role="status" className={styles.reply}>
          {CHECKIN.alreadyAnswered}
        </p>
        <p className={styles.body}>{CHECKIN.alreadyAnsweredHelp}</p>
      </section>
    );
  }

  if (result) {
    return (
      <section className={styles.card} aria-labelledby="today-checkin">
        {heading}
        <div role="status" className={styles.srOnly}>
          {CHECKIN.doneStatus}
        </div>
        <Result result={result} />
      </section>
    );
  }

  const question = needsOutcome && followUp ? followUp.question : card.question;
  const options = needsOutcome && followUp ? followUp.options : card.options;

  return (
    <section className={styles.card} aria-labelledby="today-checkin" aria-busy={busy}>
      {heading}
      {needsOutcome && <PlanQuote plan={card.plan} />}
      <div role="group" aria-labelledby="checkin-question">
        <p id="checkin-question" className={styles.question}>
          {question}
        </p>
        <div className={styles.options}>
          {options.map((o) => (
            <button
              key={o.id}
              type="button"
              className={styles.option}
              disabled={busy}
              onClick={() => (needsOutcome ? void send(cameUp ?? "", o.id) : pickFirst(o.id))}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
      {offersNote && (
        <div className={styles.note}>
          <label className={styles.checkLabel}>
            <input type="checkbox" checked={noteOn} disabled={busy} onChange={(e) => setNoteOn(e.target.checked)} />
            {CHECKIN.doctorNoteLabel}
          </label>
          {noteOn && (
            <label className={styles.fieldLabel}>
              {CHECKIN.doctorNoteField}
              <textarea
                className={styles.textarea}
                rows={3}
                maxLength={CHECKIN.doctorNoteMax}
                value={noteText}
                disabled={busy}
                onChange={(e) => setNoteText(e.target.value)}
              />
            </label>
          )}
        </div>
      )}
      {busy && (
        <p role="status" className={styles.body}>
          {CHECKIN.saving}
        </p>
      )}
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
    </section>
  );
}
