import { Link } from "react-router";
import { PLAN_TEXT } from "../../../content/app/plan";
import { guideRoute } from "../../../content/app/guides";
import type { QuickGuide } from "../../../api/funnelTypes";
import styles from "./plan.module.css";

export function QuickGuides({
  title,
  caption,
  guides,
}: {
  title: string;
  caption: string;
  guides: QuickGuide[];
}) {
  return (
    <section className={styles.guides} aria-labelledby="quick-guides">
      <h2 id="quick-guides" className={styles.guidesTitle}>
        {title}
      </h2>
      <ul className={styles.chips}>
        {guides.map((g) => (
          <li key={g.id}>
            <Link to={guideRoute(g.id)} className={styles.guideChip} data-highlight={g.highlight}>
              {g.title}
              {g.highlight && <span className={styles.forNow}>{PLAN_TEXT.forNow}</span>}
            </Link>
          </li>
        ))}
      </ul>
      <p className={styles.caption}>{caption}</p>
    </section>
  );
}
