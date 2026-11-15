import { Link, Navigate, useLocation } from "react-router";
import { GOODBYE, isGoodbyeState } from "../../../content/app/exit";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import exitStyles from "./exit.module.css";
import styles from "./settings.module.css";

/** Outside AppLayout, because the session is gone by then. Reads router state only. */
export default function GoodbyePage() {
  const state: unknown = useLocation().state;
  if (!isGoodbyeState(state)) return <Navigate to={ROUTES.home} replace />;
  const title = state.kind === "exit" ? state.title : GOODBYE.clearedTitle;
  return (
    <main id="main" tabIndex={-1} className={exitStyles.goodbye}>
      <Seo title={pageTitle(title)} description={title} />
      <meta name="robots" content="noindex" />
      <h1 className={styles.title} data-app-heading tabIndex={-1}>
        {title}
      </h1>
      {state.kind === "cleared" ? (
        <p className={styles.line}>{state.message}</p>
      ) : (
        <>
          <p className={styles.line}>{state.condolence}</p>
          <p className={styles.line}>{state.resourcesIntro}</p>
          <ul className={exitStyles.resources}>
            {state.resources.map((r) => (
              <li key={r.id} className={exitStyles.resource}>
                <p className={exitStyles.resourceName}>{r.name}</p>
                <p className={styles.note}>{r.description}</p>
                {r.phone && (
                  <a className={exitStyles.link} href={`tel:${r.phone.replace(/[^\d+]/g, "")}`}>
                    {r.phone}
                  </a>
                )}
                {r.url && (
                  <a className={exitStyles.link} href={r.url} rel="noopener noreferrer" target="_blank">
                    {r.name}
                  </a>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      <Link className={styles.secondary} to={ROUTES.home}>
        {GOODBYE.home}
      </Link>
    </main>
  );
}
