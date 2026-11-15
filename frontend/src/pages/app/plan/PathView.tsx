import { Link } from "react-router";
import { formatDate } from "../../../format/date";
import {
  PLAN_TEXT,
  doneOf,
  lessonCount,
  minutesLabel,
  moduleKicker,
  opensOn,
} from "../../../content/app/plan";
import { lessonRoute } from "../../../routes";
import type { ModuleView } from "./planModel";
import styles from "./plan.module.css";

/** Zigzag offsets of the prototype, in px at full width (halved below 520px by CSS). */
const OFFSETS = [0, 70, 110, 70, 0, -70, -110, -70];

type Lesson = ModuleView["lessons"][number];

function badgeFor(m: ModuleView): string {
  if (m.status === "current") return doneOf(m.doneCount, m.lessons.length);
  if (m.status === "later") return PLAN_TEXT.comingLater;
  return PLAN_TEXT.upNext;
}

function LessonNode({ lesson, index, current }: { lesson: Lesson; index: number; current: boolean }) {
  const style = { "--x": `${OFFSETS[index % OFFSETS.length] ?? 0}px` } as React.CSSProperties;
  const meta = `${minutesLabel(lesson.minutes)}`;
  if (lesson.status === "available" || lesson.status === "in_progress") {
    const verb = lesson.status === "in_progress" ? PLAN_TEXT.continue : PLAN_TEXT.start;
    return (
      <li className={styles.step} style={style}>
        <Link
          to={lessonRoute(lesson.id)}
          className={styles.stepLink}
          data-state={current ? "current" : "open"}
        >
          {current && <span className={styles.bubble}>{verb}</span>}
          <span className={styles.node} aria-hidden="true">{index + 1}</span>
          <span className={styles.stepTitle}>{lesson.title}</span>
          <span className={styles.stepMeta}>
            {meta}
            {current ? "" : ` · ${verb}`}
          </span>
        </Link>
      </li>
    );
  }
  const done = lesson.status === "done";
  const status = done
    ? PLAN_TEXT.done
    : lesson.status === "locked"
      ? lesson.unlockOn
        ? opensOn(formatDate(lesson.unlockOn))
        : PLAN_TEXT.opensSoon
      : PLAN_TEXT.comingLater;
  return (
    <li className={styles.step} style={style}>
      <div className={styles.stepStatic} data-state={done ? "done" : "muted"}>
        <span className={styles.node} aria-hidden="true">{done ? "✓" : index + 1}</span>
        <span className={styles.stepTitle}>{lesson.title}</span>
        <span className={styles.stepMeta}>
          {meta} · {status}
        </span>
      </div>
    </li>
  );
}

export function PathView({ modules, currentId }: { modules: ModuleView[]; currentId: string | null }) {
  const first = modules.filter((m) => m.inFirst30Days);
  const later = modules.filter((m) => !m.inFirst30Days);
  return (
    <div>
      {first.map((m, i) => (
        <section key={m.id} className={styles.module} aria-labelledby={`module-${m.id}`}>
          <div className={styles.banner} data-status={m.status}>
            <p className={styles.kicker}>{moduleKicker(i + 1, m.lessons.length)}</p>
            <h2 id={`module-${m.id}`} tabIndex={-1} className={styles.moduleTitle}>
              {m.title}
            </h2>
            <p className={styles.badge}>{badgeFor(m)}</p>
            <p className={styles.reason}>{m.reason}</p>
          </div>
          <ol className={styles.path} aria-label={m.title}>
            {m.lessons.map((l, idx) => (
              <LessonNode key={l.id} lesson={l} index={idx} current={l.id === currentId} />
            ))}
          </ol>
        </section>
      ))}
      {later.length > 0 && (
        <section aria-labelledby="after-30">
          <h2 id="after-30" className={styles.sectionTitle}>
            {PLAN_TEXT.after30Title}
          </h2>
          <ul className={styles.laterList}>
            {later.map((m) => (
              <li key={m.id} className={styles.laterCard}>
                <h3 id={`module-${m.id}`} tabIndex={-1} className={styles.cardTitle}>
                  {m.title}
                </h3>
                <p className={styles.badge}>
                  {lessonCount(m.lessons.length)} · {PLAN_TEXT.comingLater}
                </p>
                <p className={styles.reason}>{m.reason}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
