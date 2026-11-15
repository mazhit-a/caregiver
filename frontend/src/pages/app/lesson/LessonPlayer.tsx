import { useEffect, useId, useRef, useState } from "react";
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

/** Screens that must be answered before Continue (lesson 1 only; the older lessons never gated). */
const ANSWER_GATED = new Set(["scenario", "quiz", "builder", "reset"]);

/**
 * Why Continue is locked, or null. The stored step counts as the furthest reached, so screens the
 * learner already passed never lock after a reload; only the current one must be answered again.
 */
function gateFor(type: string, lesson: Lesson, answered: boolean, index: number): "setup" | "answer" | null {
  if (type === "setup" || type === "setup_question") return lesson.variant === null && !answered ? "setup" : null;
  if (lesson.screenCount === undefined || !ANSWER_GATED.has(type)) return null;
  return answered || index < lesson.progress.step ? null : "answer";
}

interface Props {
  lesson: Lesson;
  reload: () => Promise<boolean>;
}

/** The player: header (title, progress, close), the current screen, Back / Next. */
export function LessonPlayer({ lesson, reload }: Props) {
  const visible = lesson.screens.length;
  // Lesson 1 sends the full count from the first screen, so the bar never jumps when the variant is chosen.
  const total = Math.max(lesson.screenCount ?? visible, visible);
  const [index, setIndex] = useState(() => Math.min(Math.max(lesson.progress.step, 0), visible - 1));
  const [answers, setAnswers] = useState<AnswerStore>({});
  const run = useAppAction();
  const hintId = useId();
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
  const gate = gateFor(screen.type, lesson, answers[screen.id] !== undefined, index);
  const isLast = index >= visible - 1;

  function remember(screenId: string, next: (previous: AnswerEntry | undefined) => AnswerEntry) {
    setAnswers((current) => ({ ...current, [screenId]: next(current[screenId]) }));
  }

  function go(to: number) {
    moved.current = true;
    setIndex(to);
  }

  function next() {
    if (gate !== null || isLast) return;
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
        {(!isLast || gate !== null) && (
          <button
            type="button"
            className={`${styles["button"]} ${styles["primary"]}`}
            aria-disabled={gate !== null}
            aria-describedby={gate !== null ? hintId : undefined}
            onClick={next}
          >
            {screen.type === "intro" ? LESSON_COPY.start : LESSON_COPY.next}
          </button>
        )}
      </div>
      {gate !== null && (
        <p id={hintId} className={styles["hint"]}>
          {LESSON_COPY.gateHint[gate]}
        </p>
      )}
      <p className={styles["disclaimer"]}>{LESSON_COPY.notMedicalAdvice}</p>
    </div>
  );
}
