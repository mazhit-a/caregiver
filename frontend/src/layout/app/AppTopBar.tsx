import { Link, useLocation } from "react-router";
import logo from "../../assets/kelper-logo.svg";
import { ROUTES } from "../../routes";
import { HelpButton } from "./HelpButton";
import type { NavCopy } from "./navCopy";
import { isSettingsActive } from "./tabs";
import styles from "./AppChrome.module.css";

interface Props {
  copy: NavCopy | null;
  onHelp: () => void;
  /** Lesson player and practice round: Help only (the page has its own header). */
  compact: boolean;
}

/** Below 1024px: logo, Settings and the red Help button, all 48px tall. */
export function AppTopBar({ copy, onHelp, compact }: Props) {
  const { pathname } = useLocation();
  return (
    <header className={styles.topBar} data-app-chrome="top-bar">
      {!compact && (
        <Link
          to={ROUTES.today}
          className={styles.topLogo}
          aria-label="Kelper home"
        >
          <img src={logo} alt="" width={105} height={40} />
        </Link>
      )}
      <div className={styles.topEnd}>
        {!compact && copy && (
          <Link
            to={ROUTES.settings}
            className={styles.topLink}
            aria-current={isSettingsActive(pathname) ? "page" : undefined}
          >
            {copy.settings}
          </Link>
        )}
        <HelpButton className={styles.help} onClick={onHelp} />
      </div>
    </header>
  );
}
