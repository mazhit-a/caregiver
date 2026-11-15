import { useCallback, useState } from "react";
import { Link } from "react-router";
import { getSubscription } from "../../../api/app";
import { useAppCopy } from "../../../api/AppDataProvider";
import { useAppRequest } from "../../../api/useAppRequest";
import { usePricing } from "../../../api/usePricing";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { SETTINGS, STATUS_LABELS, isCancellable, statusText } from "../../../content/app/settings";
import { formatDate } from "../../../format/date";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import { ClearDataSection } from "./ClearDataSection";
import { SettingsDemo } from "./SettingsDemo";
import styles from "./settings.module.css";

const EXIT_FALLBACK = "My situation has changed";

function SubscriptionCard({ version }: { version: number }) {
  const request = useAppRequest((signal) => getSubscription(signal), [version]);
  const pricing = usePricing();
  return (
    <section className={styles.card} aria-labelledby="settings-subscription">
      <h2 className={styles.cardTitle} id="settings-subscription">
        {SETTINGS.subscriptionTitle}
      </h2>
      {request.status === "loading" && (
        <div className={styles.skeleton} role="status" aria-busy="true">
          <span className={styles.hidden}>{`Loading ${SETTINGS.loading}`}</span>
        </div>
      )}
      {request.status === "error" && !request.handled && (
        <div className={styles.error} role="alert">
          <p>{APP_ERROR_MESSAGES[request.error.kind]}</p>
          <button type="button" className={styles.retry} onClick={request.retry}>
            {SETTINGS.retry}
          </button>
        </div>
      )}
      {request.status === "ready" && (() => {
        const sub = request.data;
        const plan = pricing.status === "ready" ? pricing.data.plans.find((p) => p.id === sub.planId) : undefined;
        const date = sub.currentPeriodEnd ? formatDate(sub.currentPeriodEnd, { year: true }) : null;
        return (
          <>
            <dl className={styles.facts}>
              {plan && (
                <div className={styles.fact}>
                  <dt>{SETTINGS.planLabel}</dt>
                  <dd>{plan.label}</dd>
                </div>
              )}
              <div className={styles.fact}>
                <dt>{SETTINGS.statusLabel}</dt>
                <dd>{STATUS_LABELS[sub.status] ?? sub.status}</dd>
              </div>
              {sub.source && (
                <div className={styles.fact}>
                  <dt>{SETTINGS.modeLabel}</dt>
                  <dd>{sub.source === "demo" ? SETTINGS.modeDemo : SETTINGS.modeStripe}</dd>
                </div>
              )}
            </dl>
            <p className={styles.line}>{statusText(sub.status, date)}</p>
            {isCancellable(sub.status) && (
              <div className={styles.actions}>
                <Link className={styles.secondary} to={ROUTES.settingsCancel}>
                  {SETTINGS.cancelButton}
                </Link>
              </div>
            )}
          </>
        );
      })()}
    </section>
  );
}

export default function SettingsPage() {
  const copy = useAppCopy();
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const title = copy.data?.settings.title ?? SETTINGS.title;
  const entry = copy.data?.settings.gentleExitEntry ?? EXIT_FALLBACK;
  const hint = copy.data?.settings.gentleExitHint;
  return (
    <div className={styles.page}>
      <Seo title={pageTitle(title)} description={SETTINGS.title} />
      <meta name="robots" content="noindex" />
      <h1 className={styles.title} data-app-heading tabIndex={-1}>
        {title}
      </h1>
      <SubscriptionCard version={version} />
      <section className={styles.card} aria-labelledby="settings-privacy">
        <h2 className={styles.cardTitle} id="settings-privacy">
          {SETTINGS.privacyTitle}
        </h2>
        <p className={styles.note}>{SETTINGS.privacyNote}</p>
        <Link className={styles.calm} to={ROUTES.careCard}>
          {SETTINGS.careCardLink}
        </Link>
        <p className={styles.note}>{SETTINGS.careCardHint}</p>
        <ClearDataSection />
      </section>
      <section className={`${styles.card} ${styles.exit}`} aria-label={entry}>
        <Link className={styles.calm} to={ROUTES.settingsGentleExit}>
          {entry}
        </Link>
        {hint && <p className={styles.note}>{hint}</p>}
      </section>
      <SettingsDemo onChanged={refresh} />
    </div>
  );
}
