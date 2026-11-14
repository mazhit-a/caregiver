import { Link, Outlet } from "react-router";
import logo from "../../assets/kelper-logo.svg";
import { PUBLIC_CARD } from "../../content/app/publicCard";
import { ROUTES } from "../../routes";
import styles from "./CardLayout.module.css";

/** Public card layout: logo link and a compact disclaimer. No nav, no session code, no help sheet. */
export function CardLayout() {
  return (
    <div className={styles.shell}>
      <meta name="robots" content="noindex, nofollow" />
      <meta name="referrer" content="no-referrer" />
      <header className={styles.header}>
        <Link to={ROUTES.home} aria-label={PUBLIC_CARD.logoLink} className={styles.logo}>
          <img src={logo} alt="Kelper" width={95} height={36} />
        </Link>
        <p className={styles.disclaimer}>{PUBLIC_CARD.disclaimer}</p>
      </header>
      <Outlet />
    </div>
  );
}
