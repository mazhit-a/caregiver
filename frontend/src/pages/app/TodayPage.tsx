import { Link } from "react-router";
import { getToday } from "../../api/app";
import { useAppRequest } from "../../api/useAppRequest";
import avatar from "../../assets/ollie-avatar.png";
import { StatusBlock } from "../../components/StatusBlock";
import { TODAY } from "../../content/app/today";
import { APP_ERROR_MESSAGES } from "../../content/app/common";
import { Seo, pageTitle } from "../../layout/Seo";
import { ROUTES } from "../../routes";
import { WelcomeCard } from "./today/WelcomeCard";
import { TodayRefreshContext } from "./today/refresh";
import { SECTIONS } from "./today/sections";
import styles from "./today/today.module.css";

/** `/today`: renders what GET /api/today composes, in the API's `order`. Decides nothing itself. */
export default function TodayPage() {
  const request = useAppRequest((signal) => getToday(signal), []);

  if (request.handled) return null;
  if (request.status === "loading") {
    return (
      <>
        <h1 data-app-heading tabIndex={-1} className={styles.title}>
          Today
        </h1>
        <StatusBlock status="loading" what={TODAY.loadingWhat} onRetry={request.retry} />
      </>
    );
  }
  if (request.status === "error") {
    return (
      <>
        <h1 data-app-heading tabIndex={-1} className={styles.title}>
          Today
        </h1>
        <div role="alert">
          <p>{APP_ERROR_MESSAGES[request.error.kind]}</p>
          <button type="button" onClick={request.retry}>
            Try again
          </button>
        </div>
      </>
    );
  }

  const today = request.data;
  return (
    <>
      <Seo title={pageTitle(today.title)} description={today.title} />
      <meta name="robots" content="noindex" />
      <header className={styles.header}>
        <img src={avatar} alt={TODAY.avatarAlt} width={56} height={56} className={styles.avatar} />
        <h1 data-app-heading tabIndex={-1} className={styles.title}>
          {today.title}
        </h1>
      </header>
      <TodayRefreshContext.Provider value={request.refresh}>
      <WelcomeCard />
      <div className={styles.stack}>
        {today.order.map((name) => {
          const render = SECTIONS[name];
          return render ? <div key={name}>{render(today)}</div> : null;
        })}
      </div>
      </TodayRefreshContext.Provider>
      <nav className={styles.links} aria-label="More">
        <Link className={styles.link} to={ROUTES.visitSheet}>
          {today.visitSheetLink.label}
        </Link>
        <Link className={styles.link} to={ROUTES.careCard}>
          {TODAY.careCardLink}
        </Link>
      </nav>
    </>
  );
}
