import type { ReactNode } from "react";
import { Link } from "react-router";
import type { Today } from "../../../api/appTypes";
import { TODAY } from "../../../content/app/today";
import { ROUTES, lessonRoute } from "../../../routes";
import { CheckInSection } from "./CheckInSection";
import { DemoSection } from "./DemoSection";
import { useTodayRefresh } from "./refresh";
import styles from "./today.module.css";

type Render = (today: Today) => ReactNode;

function Bar({ done, total }: { done: number; total: number }) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  return (
    <div
      className={styles.bar}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={Math.min(done, total)}
      aria-valuetext={`${done} of ${total}`}
      aria-label={TODAY.readinessHeading}
    >
      <span className={styles.barFill} style={{ width: `${pct}%` }} />
    </div>
  );
}

function Segments({ done, target }: { done: number; target: number }) {
  return (
    <div className={styles.segments} aria-hidden="true">
      {Array.from({ length: target }, (_, i) => (
        <span key={i} className={i < done ? styles.segOn : styles.segOff} />
      ))}
    </div>
  );
}

const nextStep: Render = ({ nextStep: step }) => {
  const lesson = step.lesson;
  if (step.kind === "lesson" && lesson) {
    const cta =
      lesson.status === "available"
        ? TODAY.startLesson
        : lesson.status === "in_progress"
          ? TODAY.continueLesson
          : null;
    return (
      <section className={styles.hero} aria-labelledby="today-step">
        <p className={styles.kicker}>
          {TODAY.stepKicker} · {lesson.minutes} {TODAY.minutes}
          {lesson.skillLabel ? ` · ${lesson.skillLabel}` : ""}
        </p>
        <h2 id="today-step" className={styles.heroTitle}>
          {lesson.title}
        </h2>
        <p className={styles.body}>{lesson.reason}</p>
        {cta ? (
          <Link className={styles.cta} to={lessonRoute(lesson.lessonId)}>
            {cta}
          </Link>
        ) : (
          step.unlockText && <p className={styles.unlock}>{step.unlockText}</p>
        )}
      </section>
    );
  }
  return (
    <section className={styles.hero} aria-labelledby="today-step">
      <h2 id="today-step" className={styles.heroTitle}>
        {step.message}
      </h2>
      {step.lesson && (
        <div className={styles.upNext}>
          <p className={styles.upNextTitle}>{step.lesson.title}</p>
          {step.unlockText && <p className={styles.unlock}>{step.unlockText}</p>}
        </div>
      )}
    </section>
  );
};

const readiness: Render = ({ readiness: r }) => (
  <section className={styles.card} aria-labelledby="today-readiness">
    <h2 id="today-readiness" className={styles.cardTitle}>
      {TODAY.readinessHeading}
    </h2>
    <Bar done={r.done} total={r.total} />
    <p className={styles.body}>{r.text}</p>
  </section>
);

const weeklyRhythm: Render = ({ weeklyRhythm: w }) => (
  <section className={styles.card} aria-labelledby="today-week">
    <h2 id="today-week" className={styles.cardTitle}>
      {TODAY.weeklyHeading}
    </h2>
    <Segments done={w.done} target={w.target} />
    <p className={styles.body}>{w.text}</p>
  </section>
);

const careCardNudge: Render = ({ careCardNudge: n }) =>
  n && (
    <section className={styles.notice} aria-label={TODAY.careCardLink}>
      <p className={styles.body}>{n.text}</p>
      <Link className={styles.secondary} to={ROUTES.careCard}>
        {TODAY.updateCard}
      </Link>
    </section>
  );

const practiceRound: Render = ({ practiceRound: p }) =>
  p && (
    <section className={styles.card} aria-labelledby="today-practice">
      <p className={styles.kicker}>{TODAY.practiceKicker}</p>
      <h2 id="today-practice" className={styles.cardTitle}>
        {p.title}
      </h2>
      <p className={styles.body}>
        {p.roundsTotal} {TODAY.rounds}
      </p>
      <Link className={styles.secondary} to={ROUTES.todayPractice}>
        {TODAY.startPractice}
      </Link>
    </section>
  );

const subscriptionNotice: Render = ({ subscriptionNotice: s }) =>
  s && s.kind === "ends_on" && (
    <p className={styles.banner} role="note">
      {s.text}
    </p>
  );

const welcomeBack: Render = ({ welcomeBack: w }) =>
  w && (
    <section className={styles.banner} aria-label={w.title}>
      <h2 className={styles.bannerTitle}>{w.title}</h2>
      <p className={styles.body}>{w.body}</p>
    </section>
  );

/** The demo block, wired so a control press refreshes Today silently (the section stays mounted). */
function DemoSectionWired({ today }: { today: Today }) {
  return <DemoSection today={today} onChanged={useTodayRefresh()} />;
}

/** Section name to renderer. Unknown names in `order` are ignored; G4 and G5 fill their own files. */
export const SECTIONS: Record<string, Render> = {
  checkIn: (today) => <CheckInSection today={today} />,
  practiceRound,
  careCardNudge,
  nextStep,
  weeklyRhythm,
  readiness,
  subscriptionNotice,
  welcomeBack,
  demo: (today) => <DemoSectionWired today={today} />,
};
