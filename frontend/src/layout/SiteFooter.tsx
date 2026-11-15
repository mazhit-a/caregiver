import { Link } from "react-router";
import { ROUTES } from "../routes";
import { FOOTER_NAV, NEED_HELP_NOW } from "./nav";
import { useCrisisList } from "./useCrisisList";
import styles from "./SiteFooter.module.css";

export function SiteFooter() {
  const resources = useCrisisList().slice(0, 3);
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.band}>
          <p className={styles.bandTitle}>{NEED_HELP_NOW}</p>
          <ul className={styles.bandList}>
            {resources.map((r) => (
              <li key={r.id}>
                {r.name}: <a href={`tel:${r.phone.replace(/[^\d+]/g, "")}`}>{r.phone}</a>
              </li>
            ))}
          </ul>
        </div>
        <div className={styles.row}>
          <div className={styles.brand}>
            <p className={styles.brandName}>Kelper</p>
            <p className={styles.tagline}>One calm step at a time.</p>
          </div>
          <nav aria-label="Footer" className={styles.nav}>
            {FOOTER_NAV.map((item) => (
              <Link key={item.to} to={item.to} className={styles.link}>
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className={styles.legal}>
          {/* Placeholder domain from the design; the real address is deployment config. */}
          <p>
            <Link to={ROUTES.home} className={styles.legalLink}>
              Kelper.io
            </Link>
          </p>
        </div>
      </div>
    </footer>
  );
}
