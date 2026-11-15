import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useAppAction } from "../../../api/useAppRequest";
import { clearToken } from "../../../api/session";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import type { GoodbyeState } from "../../../content/app/exit";
import { ROUTES } from "../../../routes";
import exitStyles from "./exit.module.css";
import styles from "./settings.module.css";

interface Labels {
  facts: readonly string[];
  step2Text: string;
  continue: string;
  confirm: string;
  back: string;
  retry: string;
}

interface Props {
  labels: Labels;
  /** Runs the API call and returns the goodbye state, or throws through the action runner. */
  run: () => Promise<GoodbyeState>;
  /** Message for a 503 (blocking, nothing deleted). */
  blocked: string;
  onBack: () => void;
  headings: [string, string];
}

/**
 * Two-step destructive flow shared by the gentle exit and clear my data. The token is cleared
 * only after a 2xx; any failure keeps it and says nothing was deleted.
 */
export function ExitFlow({ labels, run, blocked, onBack, headings }: Props) {
  const navigate = useNavigate();
  const runAction = useAppAction();
  const [step, setStep] = useState<1 | 2>(1);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const pressing = useRef(false);

  async function confirm() {
    if (pressing.current) return;
    pressing.current = true;
    setBusy(true);
    setMessage(null);
    const result = await runAction(run);
    pressing.current = false;
    setBusy(false);
    if (result.ok) {
      clearToken();
      navigate(ROUTES.goodbye, { replace: true, state: result.data });
    } else if (!result.handled) {
      const { kind } = result.failure;
      setMessage(kind === "billing_failed" ? blocked : APP_ERROR_MESSAGES[kind]);
    }
  }

  return (
    <section className={styles.card} aria-labelledby="exit-step-heading">
      <h2 className={styles.cardTitle} id="exit-step-heading">
        {step === 1 ? headings[0] : headings[1]}
      </h2>
      {step === 1 ? (
        <ul className={exitStyles.list}>
          {labels.facts.map((fact) => (
            <li key={fact}>{fact}</li>
          ))}
        </ul>
      ) : (
        <p className={styles.line}>{labels.step2Text}</p>
      )}
      {message && (
        <div className={styles.error} role="alert">
          <p>{message}</p>
        </div>
      )}
      <div className={styles.actions}>
        <button type="button" className={styles.secondary} disabled={busy} onClick={onBack}>
          {labels.back}
        </button>
        {step === 1 ? (
          <button type="button" className={styles.button} onClick={() => setStep(2)}>
            {labels.continue}
          </button>
        ) : (
          <button type="button" className={exitStyles.danger} disabled={busy} aria-busy={busy} onClick={() => void confirm()}>
            {message ? labels.retry : labels.confirm}
          </button>
        )}
      </div>
    </section>
  );
}
