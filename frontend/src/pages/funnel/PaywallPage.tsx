import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { type ApiFailure, classifyError, gateRoute } from "../../api/errors";
import { createCheckout, getFunnelCopy, probeAccess, startDemo } from "../../api/funnel";
import { useRequest } from "../../api/useRequest";
import { ERROR_MESSAGES, PAYWALL } from "../../content/funnel";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { ROUTES } from "../../routes";
import { goToCheckout, isStripeCheckoutUrl } from "./checkoutRedirect";
import { PlanPicker } from "./PlanPicker";
import styles from "./PaywallPage.module.css";

type Probe = "checking" | "open";
const PLANS_LEGEND = "Choose your plan";

/** Paywall: terms and consent, then demo mode or Stripe Checkout. All wording comes from the API or content. */
export default function PaywallPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const canceled = params.get("checkout") === "canceled";
  const copy = useRequest((signal) => getFunnelCopy(signal), []);
  const [probe, setProbe] = useState<Probe>("checking");
  const [planId, setPlanId] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [consentError, setConsentError] = useState(false);
  const [busy, setBusy] = useState<"pay" | "demo" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const lock = useRef(false);
  const consentRef = useRef<HTMLInputElement>(null);
  const demoRef = useRef<HTMLButtonElement>(null);

  // Entry probe: an already-subscribed visitor goes straight to the app.
  useEffect(() => {
    const controller = new AbortController();
    probeAccess(controller.signal).then(
      () => {
        if (!controller.signal.aborted) navigate(ROUTES.today, { replace: true });
      },
      (err: unknown) => {
        if (controller.signal.aborted) return;
        const failure = classifyError(err);
        if (failure.kind === "gate" && (failure.reason === "no_plan" || failure.reason === "ended")) {
          navigate(gateRoute(failure.reason).path, { replace: true });
        } else if (failure.kind === "session_lost") navigate(ROUTES.quiz, { replace: true });
        else setProbe("open");
      },
    );
    return () => controller.abort();
  }, [navigate]);

  const failure = copy.status === "error" ? copy.error : null;
  useEffect(() => {
    if (!failure) return;
    if (failure.kind === "gate") navigate(gateRoute(failure.reason).path, { replace: true });
    else if (failure.kind === "session_lost") navigate(ROUTES.quiz, { replace: true });
  }, [failure, navigate]);

  const paywall = copy.status === "ready" ? copy.data.paywall : null;
  const plan = paywall
    ? (paywall.plans.find((p) => p.id === (planId ?? paywall.defaultPlanId)) ?? paywall.plans[0])
    : undefined;

  function handleFailure(error: unknown) {
    const f: ApiFailure = classifyError(error);
    if (f.kind === "locked" && f.code === "already_subscribed") {
      navigate(ROUTES.today, { replace: true });
    } else if (f.kind === "gate" && f.reason === "no_plan") {
      navigate(ROUTES.quiz, { replace: true });
    } else if (f.kind === "session_lost") {
      navigate(ROUTES.quiz, { replace: true });
    } else if (f.kind === "gateway" && f.demoHint) {
      setMessage(`${ERROR_MESSAGES.gateway} ${PAYWALL.demoNote}`);
      demoRef.current?.focus();
    } else setMessage(ERROR_MESSAGES[f.kind]);
  }

  async function run(kind: "pay" | "demo") {
    if (lock.current || !plan) return;
    if (!consent) {
      setConsentError(true);
      consentRef.current?.focus();
      return;
    }
    lock.current = true;
    setBusy(kind);
    setMessage(null);
    const body = { autoRenewConsent: true, planId: plan.id };
    try {
      if (kind === "demo") {
        await startDemo(body);
        navigate(ROUTES.today);
        return;
      }
      const { url } = await createCheckout(body);
      if (isStripeCheckoutUrl(url)) {
        goToCheckout(url);
        return;
      }
      setMessage(ERROR_MESSAGES.gateway);
    } catch (error) {
      handleFailure(error);
    }
    lock.current = false;
    setBusy(null);
  }

  const loading = copy.status === "loading" || probe === "checking";

  return (
    <FunnelScreen back={{ to: ROUTES.plan }}>
      <Seo title={pageTitle("Start your plan")} description="Kelper care plan." />
      <meta name="robots" content="noindex" />
      {canceled && (
        <p role="status" className={styles.banner}>
          {paywall?.states.returnedCanceled}
        </p>
      )}
      {loading && !failure && (
        <div role="status" className={styles.state}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
            {PAYWALL.loading}
          </h1>
        </div>
      )}
      {failure && (
        <div role="alert" className={styles.state}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
            {ERROR_MESSAGES[failure.kind]}
          </h1>
          <button type="button" className={styles.primary} onClick={copy.retry}>
            Try again
          </button>
          <Link to={ROUTES.plan} className={styles.link}>
            Back to your plan
          </Link>
        </div>
      )}
      {paywall && plan && probe === "open" && (
        <div className={styles.page}>
          <div className={styles.head}>
            <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
              {paywall.headline}
            </h1>
            <p className={styles.subhead}>{paywall.subhead}</p>
          </div>
          <div className={styles.includesBlock}>
            <h2 className={styles.h2}>{PAYWALL.includesTitle}</h2>
            <ul className={styles.includes}>
              {paywall.includes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <PlanPicker
            plans={paywall.plans}
            value={plan.id}
            onChange={(id) => {
              setPlanId(id);
              setConsent(false);
              setConsentError(false);
            }}
            legend={PLANS_LEGEND}
          />
          <div className={styles.disclosure} aria-live="polite">
            <p className={styles.disclosureText}>
              {plan.disclosure.map((seg, i) =>
                seg.strong ? <strong key={i}>{seg.text}</strong> : <span key={i}>{seg.text}</span>,
              )}
            </p>
          </div>
          <div className={styles.consent}>
            <label className={styles.consentLabel}>
              <input
                ref={consentRef}
                type="checkbox"
                checked={consent}
                onChange={(e) => {
                  setConsent(e.target.checked);
                  if (e.target.checked) setConsentError(false);
                }}
                aria-describedby={consentError ? "consent-error" : undefined}
                aria-invalid={consentError || undefined}
              />
              <span>{plan.consentLabel}</span>
            </label>
            <p
              id="consent-error"
              role="alert"
              className={styles.error}
              hidden={!consentError}
            >
              {consentError ? paywall.consentRequiredError : ""}
            </p>
          </div>
          <p className={styles.hint}>{PAYWALL.testModeHint}</p>
          {message && (
            <p role="alert" className={styles.error}>
              {message}
            </p>
          )}
          <button
            type="button"
            className={styles.primary}
            aria-disabled={!consent || busy !== null}
            onClick={() => void run("pay")}
          >
            {busy === "pay" ? PAYWALL.loading : plan.payButtonLabel}
          </button>
          <button
            ref={demoRef}
            type="button"
            className={styles.secondary}
            aria-disabled={!consent || busy !== null}
            onClick={() => void run("demo")}
          >
            {PAYWALL.demoButton}
          </button>
          <p className={styles.footer}>{PAYWALL.footer}</p>
        </div>
      )}
    </FunnelScreen>
  );
}
