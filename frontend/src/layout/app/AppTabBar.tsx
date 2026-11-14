import { Link, useLocation } from "react-router";
import type { NavCopy } from "./navCopy";
import { APP_TABS, isTabActive, tabLabel } from "./tabs";
import styles from "./AppChrome.module.css";

/** Below 1024px: four text-only tabs fixed to the bottom. */
export function AppTabBar({ copy }: { copy: NavCopy }) {
  const { pathname } = useLocation();
  return (
    <nav aria-label="App" className={styles.tabBar} data-app-chrome="tab-bar">
      {APP_TABS.map((tab) => (
        <Link
          key={tab.key}
          to={tab.to}
          className={styles.tab}
          aria-current={isTabActive(tab, pathname) ? "page" : undefined}
        >
          {tabLabel(copy, tab.key)}
        </Link>
      ))}
    </nav>
  );
}
