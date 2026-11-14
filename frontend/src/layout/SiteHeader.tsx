import { useState } from "react";
import { Link, NavLink } from "react-router";
import logo from "../assets/kelper-logo.svg";
import { StartLink } from "../components/marketing/StartLink";
import { ROUTES } from "../routes";
import { MAIN_NAV, NEED_HELP_NOW } from "./nav";
import styles from "./SiteHeader.module.css";

interface Props {
  onNeedHelp: () => void;
}

export function SiteHeader({ onNeedHelp }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = (): void => setMenuOpen(false);

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link to={ROUTES.home} aria-label="Kelper home" className={styles.logo}>
          <img src={logo} alt="Kelper" height={36} />
        </Link>
        <div id="site-menu" className={styles.panel} data-open={menuOpen}>
          <nav aria-label="Main" className={styles.nav}>
            {MAIN_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={closeMenu}
                className={({ isActive }) => (isActive ? `${styles.link} ${styles.active}` : styles.link)}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <StartLink onClick={closeMenu} />
        </div>
        <button type="button" className={styles.help} onClick={onNeedHelp}>
          {NEED_HELP_NOW}
        </button>
        <button
          type="button"
          className={styles.menu}
          aria-expanded={menuOpen}
          aria-controls="site-menu"
          onClick={() => setMenuOpen((o) => !o)}
        >
          Menu
        </button>
      </div>
    </header>
  );
}
