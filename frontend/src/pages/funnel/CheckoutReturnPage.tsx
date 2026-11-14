import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";
import { ApiError } from "../../api/client";
import { classifyError } from "../../api/errors";
import { getCheckoutStatus, getFunnelCopy } from "../../api/funnel";
import { getToken } from "../../api/session";
import { PAYWALL } from "../../content/funnel";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { ROUTES } from "../../routes";
import styles from "./CheckoutReturnPage.module.css";

type Outcome =
  | { status: "checking" }
  | { status: "paid" }
  | { status: "unpaid"; message: string | null }
  | { status: "error"; message: string; demoHint: boolean; retryable: boolean; toQuiz: boolean };

const TEXT = {
  checking: "Checking your payment",
  paid: "You're all set.",
  unpaid: "We haven't received the payment yet",
  unpaidBody: "It can take a moment to arrive. You can check again, or go back to your plan.",
  checkAgain: "Check again",
  continue: "Continue",
  backToPlan: "Back to your plan",
  notFound: "We couldn't find that checkout. Please go back to your plan and try again.",
  sessionLost: "We couldn't find your plan on this device. Please start again from the quiz.",
  startQuiz: "Start the quiz",
  rateLimited: "Lots of requests at once. Take a breath and try again in a minute.",
  network: "We couldn't reach the server. Check your connection and try again.",
  gateway: "Online payments aren't switched on here, so we can't confirm a payment.",
  server: "Something went wrong on our side. Please try again.",
  tryAgain: "Try again",
} as const;

function describe(error: unknown): Extract<Outcome, { status: "error" }> {
  const base = { demoHint: false, retryable: true, toQuiz: false };
  if (error instanceof ApiError && error.code === "checkout_not_found") {
    return { status: "error", ...base, message: TEXT.notFound, retryable: false };
  }
  const f = classifyError(error);
  switch (f.kind) {
    case "session_lost":
      return { status: "error", ...base, message: TEXT.sessionLost, retryable: false, toQuiz: true };
    case "rate_limited":
      return { status: "error", ...base, message: TEXT.rateLimited };
    case "network":
    case "timeout":
      return { status: "error", ...base, message: TEXT.network };
    case "gateway":
      return { status: "error", ...base, message: TEXT.gateway, demoHint: f.demoHint };
    default:
      return { status: "error", ...base, message: TEXT.server };
  }
}

/** Back from Stripe: asks the server once whether the payment arrived. No timers, no auto-redirect. */
export default function CheckoutReturnPage() {
  const [params] = useSearchParams();
  const [checkoutId] = useState(() => params.get("checkout_id"));
  const hasToken = getToken() !== null;
  if (!checkoutId) return <Navigate to={ROUTES.paywall} replace />;
  if (!hasToken) return <Navigate to={ROUTES.quiz} replace />;
  return <Reconcile checkoutId={checkoutId} />;
}

function Reconcile({ checkoutId }: { checkoutId: string }) {
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(0);
  const [outcome, setOutcome] = useState<Outcome>({ status: "checking" });
  const [successLine, setSuccessLine] = useState<string>(TEXT.paid);
  const started = useRef(-1);
  const alive = useRef(true);

  // The id is only needed once; keep it out of the address bar.
  useEffect(() => {
    window.history.replaceState(window.history.state, "", window.location.pathname);
  }, []);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  // One request per attempt; the ref guard keeps StrictMode's second mount from repeating it.
  useEffect(() => {
    if (started.current === attempt) return;
    started.current = attempt;
    setOutcome({ status: "checking" });
    getCheckoutStatus(checkoutId).then(
      (result) => {
        if (!alive.current) return;
        setOutcome(result.paid ? { status: "paid" } : { status: "unpaid", message: result.message });
        if (result.paid) {
          getFunnelCopy().then(
            (copy) => {
              if (alive.current) setSuccessLine(copy.paywall.states.success);
            },
            () => undefined,
          );
        }
      },
      (error: unknown) => {
        if (alive.current) setOutcome(describe(error));
      },
    );
  }, [attempt, checkoutId]);

  const again = () => setAttempt((n) => n + 1);
  const heading =
    outcome.status === "checking"
      ? TEXT.checking
      : outcome.status === "paid"
        ? successLine
        : outcome.status === "unpaid"
          ? TEXT.unpaid
          : outcome.message;

  return (
    <FunnelScreen>
      <Seo title={pageTitle("Checking your payment")} description="Kelper care plan." />
      <meta name="robots" content="noindex" />
      <div
        className={styles.state}
        role={outcome.status === "error" ? "alert" : "status"}
        aria-live={outcome.status === "error" ? undefined : "polite"}
      >
        <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
          {heading}
        </h1>
        {outcome.status === "unpaid" && (
          <p className={styles.body}>{outcome.message ?? TEXT.unpaidBody}</p>
        )}
        {outcome.status === "error" && outcome.demoHint && (
          <p className={styles.body}>{PAYWALL.demoNote}</p>
        )}
      </div>
      {outcome.status === "paid" && (
        <button type="button" className={styles.primary} onClick={() => navigate(ROUTES.today)}>
          {TEXT.continue}
        </button>
      )}
      {(outcome.status === "unpaid" || (outcome.status === "error" && outcome.retryable)) && (
        <button type="button" className={styles.primary} onClick={again}>
          {outcome.status === "unpaid" ? TEXT.checkAgain : TEXT.tryAgain}
        </button>
      )}
      {outcome.status === "error" && outcome.toQuiz && (
        <Link to={ROUTES.quiz} className={styles.link}>
          {TEXT.startQuiz}
        </Link>
      )}
      {(outcome.status === "unpaid" || (outcome.status === "error" && !outcome.toQuiz)) && (
        <Link to={ROUTES.paywall} className={styles.link}>
          {TEXT.backToPlan}
        </Link>
      )}
    </FunnelScreen>
  );
}
