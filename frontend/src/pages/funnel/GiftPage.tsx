import { useEffect } from "react";
import { Link, useNavigate } from "react-router";
import { getGift } from "../../api/funnel";
import { gateRoute } from "../../api/errors";
import { useRequest } from "../../api/useRequest";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { ROUTES } from "../../routes";
import styles from "./GiftPage.module.css";

/** The free phrase sheet. Everything shown comes from GET /plan/gift; print CSS makes it one Letter page. */
export default function GiftPage() {
  const navigate = useNavigate();
  const gift = useRequest((signal) => getGift(signal), []);
  const failure = gift.status === "error" ? gift.error : null;

  useEffect(() => {
    if (!failure) return;
    if (failure.kind === "gate") navigate(gateRoute(failure.reason).path, { replace: true });
    else if (failure.kind === "session_lost") navigate(ROUTES.quiz, { replace: true });
  }, [failure, navigate]);

  const empty = gift.status === "ready" && gift.data.phrases.length === 0;

  return (
    <FunnelScreen back={{ to: ROUTES.plan }}>
      <Seo
        title={pageTitle("Your free phrase sheet")}
        description="A one-page sheet of calm phrases you can print."
      />
      <meta name="robots" content="noindex" />
      {gift.status === "loading" && (
        <div role="status" className={styles.state}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.stateTitle}>
            Getting your sheet
          </h1>
          <p>One moment.</p>
        </div>
      )}
      {(gift.status === "error" || empty) && (
        <div role="alert" className={styles.state}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.stateTitle}>
            We couldn't load your sheet
          </h1>
          <p>Please try again. Your plan is safe.</p>
          <button type="button" className={styles.button} onClick={gift.retry}>
            Try again
          </button>
          <Link to={ROUTES.plan} className={styles.link}>
            Back to your plan
          </Link>
        </div>
      )}
      {gift.status === "ready" && !empty && (
        <div className={styles.sheet}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
            {gift.data.title}
          </h1>
          <p className={styles.intro}>{gift.data.intro}</p>
          <ol className={styles.phrases}>
            {gift.data.phrases.map((phrase) => (
              <li key={phrase.id} className={styles.phrase}>
                <p className={styles.text}>{phrase.text}</p>
                <p className={styles.when}>{phrase.when}</p>
              </li>
            ))}
          </ol>
          <p className={styles.footer}>{gift.data.footer}</p>
          <div className={styles.actions}>
            <button type="button" className={styles.button} onClick={() => window.print()}>
              Print or save as PDF
            </button>
            <Link to={ROUTES.plan} className={styles.link}>
              Back to your plan
            </Link>
          </div>
        </div>
      )}
    </FunnelScreen>
  );
}
