import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import { completeQuiz, getFunnelCopy, getPlanPreview } from "../../api/funnel";
import { type ApiFailure, gateRoute, missingQuestionIds } from "../../api/errors";
import { useRequest } from "../../api/useRequest";
import ollieBuilding from "../../assets/funnel/ollie-building.webp";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { quizQuestionRoute, ROUTES } from "../../routes";
import styles from "./BuildingPage.module.css";

/** Where a failure sends the user, or null when the page shows a message with Try again. */
function failureRoute(failure: ApiFailure): { to: string; restore?: boolean } | null {
  switch (failure.kind) {
    case "gate":
      return { to: gateRoute(failure.reason).path };
    case "session_lost":
      return { to: ROUTES.quiz, restore: true };
    case "locked":
      return { to: ROUTES.today };
    case "validation": {
      const [first] = missingQuestionIds(failure);
      return first ? { to: quizQuestionRoute(first) } : null;
    }
    default:
      return null;
  }
}

/**
 * Builds the plan (complete is idempotent), then shows the API's loader lines.
 * No artificial wait: the lines appear when the data is back, and the button is enabled at once.
 */
export default function BuildingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const build = useRequest(async (signal) => {
    await completeQuiz(signal);
    const [preview, copy] = await Promise.all([getPlanPreview(signal), getFunnelCopy(signal)]);
    return { lines: preview.loaderLines, title: copy.loader.title, cta: copy.planPreview.cta };
  }, []);

  const failure = build.status === "error" ? build.error : null;
  const route = failure ? failureRoute(failure) : null;

  useEffect(() => {
    if (!route) return;
    navigate(route.to, { replace: true, state: route.restore ? { restore: true } : null });
  }, [route, navigate]);

  const goBack = () => {
    if (location.key !== "default") navigate(-1);
    else navigate(ROUTES.quiz);
  };

  return (
    <FunnelScreen
      back={{ onClick: goBack }}
      actionBar={
        build.status === "ready" ? (
          <button type="button" className={styles.button} onClick={() => navigate(ROUTES.plan)}>
            {build.data.cta}
          </button>
        ) : undefined
      }
    >
      <Seo title={pageTitle("Building your plan")} description="Kelper care plan." />
      <meta name="robots" content="noindex" />
      <div className={styles.screen}>
        <img src={ollieBuilding} alt="" width={150} height={186} className={styles.ollie} />
        {build.status === "loading" && (
          <div role="status" className={styles.block}>
            <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
              Building your plan
            </h1>
          </div>
        )}
        {build.status === "error" && !route && (
          <div role="alert" className={styles.block}>
            <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
              We couldn't build your plan
            </h1>
            <p>Your answers are saved. Please try again.</p>
            <button type="button" className={styles.button} onClick={build.retry}>
              Try again
            </button>
          </div>
        )}
        {build.status === "ready" && (
          <div className={styles.block}>
            <h1 data-funnel-heading tabIndex={-1} className={styles.title}>
              {build.data.title}
            </h1>
            <div role="status" aria-label={build.data.title}>
              <ul className={styles.lines}>
                {build.data.lines.map((line) => (
                  <li key={line} className={styles.line}>
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </FunnelScreen>
  );
}
