import { PLAN_TEXT, QG_LIMIT_ID } from "../../../content/app/plan";
import type { QuickGuide } from "../../../api/funnelTypes";
import styles from "./plan.module.css";

export function QuickGuides({
  title,
  caption,
  guides,
  onLimit,
}: {
  title: string;
  caption: string;
  guides: QuickGuide[];
  onLimit: () => void;
}) {
  return (
    <section className={styles.guides} aria-labelledby="quick-guides">
      <h2 id="quick-guides" className={styles.guidesTitle}>
        {title}
      </h2>
      <ul className={styles.chips}>
        {guides.map((g) => (
          <li key={g.id}>
            {g.id === QG_LIMIT_ID ? (
              <button type="button" className={styles.guideChip} data-highlight={g.highlight} onClick={onLimit}>
                {g.title}
                {g.highlight && <span className={styles.forNow}>{PLAN_TEXT.forNow}</span>}
              </button>
            ) : (
              <span className={styles.guideChip} data-highlight={g.highlight}>
                {g.title}
                {g.highlight && <span className={styles.forNow}>{PLAN_TEXT.forNow}</span>}
              </span>
            )}
          </li>
        ))}
      </ul>
      <p className={styles.caption}>{caption}</p>
    </section>
  );
}
