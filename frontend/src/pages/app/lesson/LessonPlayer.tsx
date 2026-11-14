import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { putLessonProgress } from "../../../api/app";
import type { Lesson } from "../../../api/appTypes";
import { useAppAction } from "../../../api/useAppRequest";
import { LESSON_COPY } from "../../../content/app/lesson";
import { Seo, pageTitle } from "../../../layout/Seo";
import { ROUTES } from "../../../routes";
import { ScreenView } from "./screens/registry";
import type { AnswerEntry, AnswerStore } from "./screens/types";
import styles from "./lesson.module.css";

interface Props {
  lesson: Lesson;
  reload: () => Promise<boolean>;
}

/** The player: header (title, progress, close), the current screen, Back / Next. */
export function LessonPlayer({ lesson, reload }: Props) {
  const total = lesson.screens.length;
  const [index, setIndex] = useState(() => Math.min(Math.max(lesson.progress.step, 0), total - 1));
  const [answers, setAnswers] = useState<AnswerStore>({});
  const run = useAppAction();
  const stage = useRef<HTMLDivElement>(null);
  const moved = useRef(false);

  useEffect(() => {
    if (!moved.current) return;
    const target = stage.current?.querySelector<HTMLElement>("[data-screen-heading]") ?? stage.current;
    target?.focus();
    window.scrollTo?.(0, 0);
  }, [index]);

  const screen = lesson.screens[index];
  if (!screen) return null;
  const waitingForSetup = screen.type === "setup_question" && lesson.variant === null;
  const isLast = index >= total - 1;

  function remember(screenId: string, next: (previous: AnswerEntry | undefined) => AnswerEntry) {
    setAnswers((current) => ({ ...current, [screenId]: next(current[screenId]) }));
  }

  function go(to: number) {
    moved.current = true;
    setIndex(to);
  }

  function next() {
    if (waitingForSetup || isLast) return;
    const to = index + 1;
    go(to);
    void run(() => putLessonProgress(lesson.id, to));
  }

  const position = index + 1;
  return (
    <div className={styles["player"]}>
      <Seo title={pageTitle(lesson.title)} description={lesson.skillLabel} />
      <meta name="robots" content="noindex" />
      <header className={styles["header"]}>
        <div className={styles["top"]}>
          <h1 className={styles["h1"]} data-app-heading tabIndex={-1}>
            {lesson.title}
          </h1>
          <Link to={ROUTES.today} className={styles["close"]} aria-label={LESSON_COPY.closeLesson}>
            {LESSON_COPY.closeShort}
          </Link>
        </div>
        <div className={styles["progress"]}>
          <div
            className={styles["bar"]}
            role="progressbar"
            aria-label={LESSON_COPY.progressLabel}
            aria-valuemin={1}
            aria-valuemax={total}
            aria-valuenow={position}
            aria-valuetext={`Screen ${position} of ${total}`}
          >
            <div className={styles["fill"]} style={{ width: `${(position / total) * 100}%` }} />
          </div>
          <span className={styles["count"]}>
            {position} of {total}
          </span>
        </div>
      </header>
      <div className={styles["stage"]} ref={stage} tabIndex={-1}>
        {index === 0 && lesson.recap && (
          <p className={styles["recap"]}>
            <strong>{LESSON_COPY.recapLabel}:</strong> {lesson.recap.text}
          </p>
        )}
        <ScreenView
          key={screen.id}
          screen={screen}
          lesson={lesson}
          entry={answers[screen.id]}
          answers={answers}
          remember={remember}
          reload={reload}
        />
      </div>
      <div className={styles["footer"]}>
        {index > 0 && (
          <button type="button" className={`${styles["button"]} ${styles["ghost"]}`} onClick={() => go(index - 1)}>
            {LESSON_COPY.back}
          </button>
        )}
        {(!isLast || waitingForSetup) && (
          <button
            type="button"
            className={`${styles["button"]} ${styles["primary"]}`}
            aria-disabled={waitingForSetup}
            onClick={next}
          >
            {waitingForSetup ? LESSON_COPY.nextSetup : LESSON_COPY.next}
          </button>
        )}
      </div>
      <p className={styles["disclaimer"]}>{LESSON_COPY.notMedicalAdvice}</p>
    </div>
  );
}
