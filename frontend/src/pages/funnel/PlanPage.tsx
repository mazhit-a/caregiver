import { useEffect } from "react";
import { useNavigate } from "react-router";
import { getFunnelCopy, getPlanPreview } from "../../api/funnel";
import { gateRoute } from "../../api/errors";
import { useRequest } from "../../api/useRequest";
import { DISCLAIMER } from "../../content/funnel";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { ROUTES } from "../../routes";
import { GiftCard } from "./plan/GiftCard";
import {
  BeforeAfterCards,
  First30Days,
  QuickGuides,
  WhatWeHeard,
  WhyThisWorks,
} from "./plan/PlanSections";
import styles from "./PlanPage.module.css";

/** Renders the stored plan exactly as the API returns it. Slices only by inFirst30Days and status. */
export default function PlanPage() {
  const navigate = useNavigate();
  const plan = useRequest(async (signal) => {
    const [preview, copy] = await Promise.all([getPlanPreview(signal), getFunnelCopy(signal)]);
    return { preview, copy };
  }, []);
  const failure = plan.status === "error" ? plan.error : null;
  const redirectTo =
    failure?.kind === "gate"
      ? gateRoute(failure.reason).path
      : failure?.kind === "session_lost"
        ? ROUTES.quiz
        : null;
  const restore = failure?.kind === "session_lost";

  useEffect(() => {
    if (!redirectTo) return;
    navigate(redirectTo, { replace: true, state: restore ? { restore: true } : null });
  }, [redirectTo, restore, navigate]);

  const goPaywall = () => navigate(ROUTES.paywall);

  return (
    <FunnelScreen
      back={{ to: ROUTES.quizBuilding }}
      actionBar={
        plan.status === "ready" ? (
          <button type="button" className={styles.button} onClick={goPaywall}>
            {plan.data.copy.planPreview.cta}
          </button>
        ) : undefined
      }
    >
      <Seo title={pageTitle("Your plan")} description="Kelper care plan." />
      <meta name="robots" content="noindex" />
      {plan.status === "loading" && (
        <div role="status" className={styles.state}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
            Getting your plan
          </h1>
          <p>One moment.</p>
        </div>
      )}
      {plan.status === "error" && !redirectTo && (
        <div role="alert" className={styles.state}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
            We couldn't load your plan
          </h1>
          <p>Your answers are saved. Please try again.</p>
          <button type="button" className={styles.button} onClick={plan.retry}>
            Try again
          </button>
        </div>
      )}
      {plan.status === "ready" && (
        <div className={styles.page}>
          <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
            {plan.data.copy.planPreview.title}
          </h1>
          <p className={styles.intro}>{plan.data.preview.planIntro}</p>
          <WhatWeHeard sentences={plan.data.preview.whatWeHeard} />
          <BeforeAfterCards value={plan.data.preview.beforeAfter} />
          <First30Days modules={plan.data.preview.modules} paceLabel={plan.data.preview.pace.label} />
          <QuickGuides
            guides={plan.data.preview.quickGuides}
            highlightLabel={plan.data.copy.planPreview.highlightLabel}
          />
          <WhyThisWorks />
          <GiftCard />
          <p className={styles.disclaimer}>{DISCLAIMER}</p>
        </div>
      )}
    </FunnelScreen>
  );
}
