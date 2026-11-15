import { useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router";
import logo from "../../assets/kelper-logo.svg";
import { GUIDES_TEXT } from "../../content/app/guides";
import { HelpSheet } from "../../layout/HelpSheet";
import { NEED_HELP_NOW } from "../../layout/nav";
import { ROUTES } from "../../routes";
import styles from "./GuideLayout.module.css";

/** Public guide shell: logo, Back and the help button. No sidebar, no session, no Ollie. */
export function GuideLayout() {
  const [helpOpen, setHelpOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const goBack = (event: React.MouseEvent<HTMLAnchorElement>): void => {
    // "default" means this is the first screen of the visit: fall through to the home link.
    if (location.key !== "default") {
      event.preventDefault();
      void navigate(-1);
    }
  };
  return (
    <div className={styles.shell}>
      <meta name="robots" content="noindex, nofollow" />
      <header className={styles.header}>
        <Link to={ROUTES.home} aria-label={GUIDES_TEXT.logoLink} className={styles.logo}>
          <img src={logo} alt="Kelper" width={95} height={36} />
        </Link>
        <Link to={ROUTES.home} className={styles.back} onClick={goBack}>
          {GUIDES_TEXT.back}
        </Link>
        <button type="button" className={styles.help} onClick={() => setHelpOpen(true)}>
          {NEED_HELP_NOW}
        </button>
      </header>
      <main id="main" tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
      <HelpSheet open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
