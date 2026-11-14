import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { getLesson } from "../../../api/app";
import type { Lesson } from "../../../api/appTypes";
import { useAppAction, useAppRequest } from "../../../api/useAppRequest";
import { APP_ERROR_MESSAGES } from "../../../content/app/common";
import { LESSON_COPY } from "../../../content/app/lesson";
import { formatDate } from "../../../format/date";
import { Seo, pageTitle } from "../../../layout/Seo";
import { StatusBlock } from "../../../components/StatusBlock";
import { ROUTES } from "../../../routes";
import { LessonPlayer } from "./LessonPlayer";
import styles from "./lesson.module.css";

function Notice({ title, body }: { title: string; body?: string }) {
  return (
    <div className={styles["notice"]}>
      <Seo title={pageTitle(title)} description={title} />
      <meta name="robots" content="noindex" />
      <h1 data-app-heading tabIndex={-1}>
        {title}
      </h1>
      {body && <p>{body}</p>}
      <Link to={ROUTES.today} className={styles["link"]}>
        {LESSON_COPY.toToday}
      </Link>
    </div>
  );
}

export default function LessonPage() {
  const { lessonId = "" } = useParams();
  return <LessonLoader key={lessonId} lessonId={lessonId} />;
}

function LessonLoader({ lessonId }: { lessonId: string }) {
  const request = useAppRequest((signal) => getLesson(lessonId, signal), [lessonId]);
  const run = useAppAction();
  const [fresh, setFresh] = useState<Lesson | null>(null);

  const reload = useCallback(async (): Promise<boolean> => {
    const outcome = await run(() => getLesson(lessonId));
    if (outcome.ok) setFresh(outcome.data);
    return outcome.ok;
  }, [run, lessonId]);

  if (request.status === "loading") {
    return <StatusBlock status="loading" what={LESSON_COPY.loadingWhat} onRetry={request.retry} />;
  }
  if (request.status === "error") {
    if (request.handled) return null;
    const failure = request.error;
    if (failure.kind === "lesson_locked") {
      const body = failure.unlockOn
        ? LESSON_COPY.lockedOn(formatDate(failure.unlockOn))
        : LESSON_COPY.lockedUndated;
      return <Notice title={LESSON_COPY.lockedTitle} body={body} />;
    }
    if (failure.kind === "not_found") {
      return <Notice title={LESSON_COPY.notFoundTitle} body={APP_ERROR_MESSAGES.not_found} />;
    }
    return <StatusBlock status="error" what={LESSON_COPY.loadingWhat} onRetry={request.retry} />;
  }
  const lesson = fresh ?? request.data;
  if (lesson.screens.length === 0) return <Notice title={lesson.title} />;
  return <LessonPlayer lesson={lesson} reload={reload} />;
}
