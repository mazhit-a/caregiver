import { Link } from "react-router";
import { PLAN_TEXT, lessonsDoneOf } from "../../../content/app/plan";
import { lessonRoute } from "../../../routes";
import { firstOpenLesson, type ModuleView } from "./planModel";
import styles from "./plan.module.css";

function chipFor(status: string): string {
  if (status === "current") return PLAN_TEXT.current;
  if (status === "later") return PLAN_TEXT.comingLater;
  return PLAN_TEXT.upNext;
}

export function ModulesGrid({
  modules,
  onShowInPath,
}: {
  modules: ModuleView[];
  onShowInPath: (moduleId: string) => void;
}) {
  return (
    <ul className={styles.grid}>
      {modules.map((m) => {
        const open = firstOpenLesson(m);
        const total = m.lessons.length;
        return (
          <li key={m.id} className={styles.card} data-status={m.status}>
            <div className={styles.band}>
              <span className={styles.chip}>{chipFor(m.status)}</span>
            </div>
            <h2 className={styles.cardTitle}>{m.title}</h2>
            <p className={styles.count}>{lessonsDoneOf(m.doneCount, total)}</p>
            <div
              className={styles.bar}
              role="progressbar"
              aria-label={`${m.title}: ${lessonsDoneOf(m.doneCount, total)}`}
              aria-valuemin={0}
              aria-valuemax={total}
              aria-valuenow={m.doneCount}
            >
              <span style={{ width: total ? `${(m.doneCount / total) * 100}%` : "0%" }} />
            </div>
            <p className={styles.reason}>{m.reason}</p>
            {open ? (
              <Link to={lessonRoute(open.id)} className={styles.cardAction}>
                {PLAN_TEXT.openLesson}
                <span className={styles.srOnly}>: {open.title}</span>
              </Link>
            ) : (
              <button type="button" className={styles.cardAction} onClick={() => onShowInPath(m.id)}>
                {PLAN_TEXT.seeInPath}
                <span className={styles.srOnly}>: {m.title}</span>
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
