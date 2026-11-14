import { Link, useNavigate } from "react-router";
import { getToday } from "../../../api/app";
import { useAppRequest } from "../../../api/useAppRequest";
import { StatusBlock } from "../../../components/StatusBlock";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { COACH_COPY } from "../../../content/app/coach";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import { RoleplayRoom } from "./RoleplayRoom";
import styles from "./roleplay.module.css";

/** `/today/practice`: the 2-minute practice round that Today offers. Same room, context "practice_round". */
export default function PracticeRoundPage() {
  const request = useAppRequest((signal) => getToday(signal), []);
  const navigate = useNavigate();
  if (request.handled) return null;

  const head = (
    <>
      <Seo title={pageTitle(COACH_COPY.practicePageTitle)} description={COACH_COPY.practicePageTitle} />
      <meta name="robots" content="noindex" />
      <h1 data-app-heading tabIndex={-1}>
        {COACH_COPY.practicePageTitle}
      </h1>
    </>
  );

  if (request.status === "loading") {
    return (
      <>
        {head}
        <StatusBlock status="loading" what={COACH_COPY.practiceLoading} onRetry={request.retry} />
      </>
    );
  }
  if (request.status === "error") {
    return (
      <>
        {head}
        <div role="alert" className={styles["errorBox"]}>
          <p className={styles["text"]}>{APP_ERROR_MESSAGES[request.error.kind]}</p>
          <button type="button" className={styles["secondary"]} onClick={request.retry}>
            {COACH_COPY.tryAgain}
          </button>
        </div>
      </>
    );
  }

  const practice = request.data.practiceRound;
  if (!practice) {
    return (
      <>
        {head}
        <h2 className={styles["h"]}>{COACH_COPY.practiceMissingTitle}</h2>
        <p className={styles["text"]}>{COACH_COPY.practiceMissingBody}</p>
        <Link className={styles["secondary"]} to={ROUTES.today}>
          {COACH_COPY.backToToday}
        </Link>
      </>
    );
  }

  return (
    <>
      {head}
      <p className={styles["muted"]}>{practice.title}</p>
      <RoleplayRoom
        lessonId={practice.lessonId}
        context="practice_round"
        onDone={() => void navigate(ROUTES.today)}
      />
      <Link className={styles["backLink"]} to={ROUTES.today}>
        {COACH_COPY.backToToday}
      </Link>
    </>
  );
}
