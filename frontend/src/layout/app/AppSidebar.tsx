import { Link, useLocation } from "react-router";
import logo from "../../assets/kelper-logo.svg";
import { ROUTES } from "../../routes";
import { HelpButton } from "./HelpButton";
import type { NavCopy } from "./navCopy";
import { APP_TABS, isSettingsActive, isTabActive, tabLabel } from "./tabs";
import styles from "./AppChrome.module.css";

interface Props {
  copy: NavCopy | null;
  onHelp: () => void;
}

/** Desktop (1024px and up): logo, four tabs, Settings, Help. */
export function AppSidebar({ copy, onHelp }: Props) {
  const { pathname } = useLocation();
  return (
    <aside className={styles.sidebar} data-app-chrome="sidebar">
      <Link to={ROUTES.today} className={`${styles.logo} ${styles.sideLogo}`} aria-label="Kelper home">
        <img src={logo} alt="" width={253} height={96} />
      </Link>
      {copy && (
        <nav aria-label="App" className={styles.sideNav}>
          {APP_TABS.map((tab) => (
            <Link
              key={tab.key}
              to={tab.to}
              className={styles.sideTab}
              aria-current={isTabActive(tab, pathname) ? "page" : undefined}
            >
              {tabLabel(copy, tab.key)}
            </Link>
          ))}
          <Link
            to={ROUTES.settings}
            className={styles.sideTab}
            aria-current={isSettingsActive(pathname) ? "page" : undefined}
          >
            {copy.settings}
          </Link>
        </nav>
      )}
      <div className={styles.sideBottom}>
        <HelpButton className={styles.help} onClick={onHelp} />
      </div>
    </aside>
  );
}
