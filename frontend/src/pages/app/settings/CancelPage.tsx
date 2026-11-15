import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { cancelSubscription, getCancelPreview } from "../../../api/app";
import { useAppAction, useAppRequest } from "../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { CANCEL, cancelFacts, canceledText, isCancellable } from "../../../content/app/settings";
import { formatDate } from "../../../format/date";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import styles from "./settings.module.css";

type Outcome = { kind: "done"; endDate: string | null } | { kind: "blocked" } | { kind: "conflict" } | { kind: "error"; message: string };

const show = (iso: string | null): string | null => (iso ? formatDate(iso, { year: true }) : null);

export default function CancelPage() {
  const navigate = useNavigate();
  const preview = useAppRequest((signal) => getCancelPreview(signal), []);
  const runAction = useAppAction();
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const pressing = useRef(false);

  async function cancel() {
    if (pressing.current) return;
    pressing.current = true;
    setBusy(true);
    const result = await runAction(() => cancelSubscription());
    pressing.current = false;
    setBusy(false);
    if (result.ok) {
      setOutcome({ kind: "done", endDate: result.data.endDate });
    } else if (!result.handled) {
      const { kind } = result.failure;
      setOutcome(
        kind === "billing_failed"
          ? { kind: "blocked" }
          : kind === "conflict"
            ? { kind: "conflict" }
            : { kind: "error", message: APP_ERROR_MESSAGES[kind] },
      );
    }
  }

  const data = preview.status === "ready" ? preview.data : null;
  const message =
    outcome?.kind === "blocked"
      ? CANCEL.blocked
      : outcome?.kind === "conflict"
        ? CANCEL.conflict
        : outcome?.kind === "error"
          ? outcome.message
          : null;
  return (
    <div className={styles.page}>
      <Seo title={pageTitle(CANCEL.title)} description={CANCEL.title} />
      <meta name="robots" content="noindex" />
      <h1 className={styles.title} data-app-heading tabIndex={-1}>
        {CANCEL.title}
      </h1>
      {preview.status === "loading" && (
        <div className={styles.skeleton} role="status" aria-busy="true">
          <span className={styles.hidden}>{`Loading ${CANCEL.loading}`}</span>
        </div>
      )}
      {preview.status === "error" && !preview.handled && (
        <div className={styles.error} role="alert">
          <p>{APP_ERROR_MESSAGES[preview.error.kind]}</p>
          <button type="button" className={styles.retry} onClick={preview.retry}>
            {CANCEL.retry}
          </button>
        </div>
      )}
      {outcome?.kind === "done" && (
        <section className={`${styles.card} ${styles.done}`} aria-labelledby="cancel-done" role="status">
          <h2 className={styles.cardTitle} id="cancel-done">
            {CANCEL.doneTitle}
          </h2>
          <p className={styles.line}>{canceledText(show(outcome.endDate))}</p>
          <Link className={styles.secondary} to={ROUTES.settings}>
            {CANCEL.back}
          </Link>
        </section>
      )}
      {data && outcome?.kind !== "done" && !isCancellable(data.status) && (
        <section className={styles.card}>
          <p className={styles.line}>{data.status === "canceling" ? CANCEL.alreadyCanceling : CANCEL.notCancellable}</p>
          {data.status === "canceling" && <p className={styles.line}>{canceledText(show(data.endDate))}</p>}
          <Link className={styles.secondary} to={ROUTES.settings}>
            {CANCEL.back}
          </Link>
        </section>
      )}
      {data && outcome?.kind !== "done" && isCancellable(data.status) && (
        <section className={styles.card} aria-label={CANCEL.title}>
          <p className={styles.line}>
            {cancelFacts({
              planName: data.planName,
              savedPhraseCount: data.savedPhraseCount,
              careCardPublished: data.careCardPublished,
              endDate: show(data.endDate),
            })}
          </p>
          {message && (
            <div className={styles.error} role="alert">
              <p>{message}</p>
            </div>
          )}
          <div className={styles.actions}>
            <button type="button" className={styles.secondary} disabled={busy} onClick={() => navigate(ROUTES.settings)}>
              {CANCEL.keep}
            </button>
            <button type="button" className={styles.button} disabled={busy} aria-busy={busy} onClick={() => void cancel()}>
              {outcome?.kind === "blocked" ? CANCEL.retry : CANCEL.confirm}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
