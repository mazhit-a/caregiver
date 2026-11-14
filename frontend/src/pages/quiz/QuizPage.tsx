import { useCallback, useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { clearToken, getToken } from "../../api/session";
import { ApiError } from "../../api/client";
import { type ApiFailure, classifyError, missingQuestionIds } from "../../api/errors";
import { completeQuiz, createSession, getQuiz } from "../../api/funnel";
import type { QuizState } from "../../api/funnelTypes";
import waving from "../../assets/home/ollie-waving.webp";
import { ActionBar } from "../../components/funnel/ActionBar";
import { ERROR_MESSAGES, QUIZ_INTRO, RESTORE_FAILED } from "../../content/funnel";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { quizQuestionRoute, ROUTES } from "../../routes";
import { QUIZ_UI } from "./quizCopy";
import { failureRoute, resumeIndex } from "./quizSteps";
import styles from "./quiz.module.css";

type Entry =
  | { status: "checking" }
  | { status: "intro" }
  | { status: "go"; to: string }
  | { status: "error"; failure: ApiFailure };

/** Decides what `/quiz` shows for the current token (locked, completed, mid-quiz or fresh). */
async function resolveEntry(quiz: QuizState): Promise<Entry> {
  if (quiz.locked) return { status: "go", to: ROUTES.today };
  if (quiz.completed) {
    try {
      await completeQuiz(); // rebuilds, so an edited answer never leaves a stale plan
      return { status: "go", to: ROUTES.plan };
    } catch (err: unknown) {
      const failure = classifyError(err);
      const missing = missingQuestionIds(failure)[0];
      if (missing) return { status: "go", to: quizQuestionRoute(missing) };
      const route = failureRoute(failure);
      return route ? { status: "go", to: route } : { status: "error", failure };
    }
  }
  const idx = resumeIndex(quiz);
  const target = quiz.questions[idx];
  if (quiz.lastQuestionId !== null && target) {
    return { status: "go", to: quizQuestionRoute(target.id) };
  }
  return { status: "intro" };
}

export default function QuizPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const restored = (location.state as { restore?: boolean } | null)?.restore === true;
  const [notice, setNotice] = useState(restored);
  const [entry, setEntry] = useState<Entry>(
    getToken() ? { status: "checking" } : { status: "intro" },
  );
  const [busy, setBusy] = useState(false);
  const [startError, setStartError] = useState<ApiFailure | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!getToken()) return;
    let live = true;
    getQuiz()
      .then(resolveEntry)
      .then((next) => live && setEntry(next))
      .catch((err: unknown) => {
        if (!live) return;
        const failure = classifyError(err);
        if (failure.kind === "session_lost") {
          clearToken();
          setNotice(true);
          setEntry({ status: "intro" });
        } else setEntry({ status: "error", failure });
      });
    return () => {
      live = false;
    };
  }, [attempt]);

  const start = useCallback(async () => {
    setBusy(true);
    setStartError(null);
    try {
      if (!getToken()) await createSession();
      let quiz: QuizState;
      try {
        quiz = await getQuiz();
      } catch (err: unknown) {
        if (!(err instanceof ApiError) || err.status !== 401) throw err;
        clearToken();
        await createSession();
        quiz = await getQuiz();
      }
      const idx = resumeIndex(quiz);
      const first = quiz.questions[quiz.lastQuestionId === null ? 0 : idx];
      if (first) navigate(quizQuestionRoute(first.id));
      else setStartError({ kind: "unknown" });
    } catch (err: unknown) {
      setStartError(classifyError(err));
    } finally {
      setBusy(false);
    }
  }, [navigate]);

  if (entry.status === "go") return <Navigate to={entry.to} replace />;

  const failure = entry.status === "error" ? entry.failure : startError;
  const checking = entry.status === "checking";

  return (
    <FunnelScreen
      back={{ to: ROUTES.home }}
      actionBar={
        entry.status === "intro" && (
          <ActionBar
            primary={{
              label: busy ? QUIZ_UI.saving : QUIZ_INTRO.cta,
              disabled: busy,
              onClick: () => void start(),
            }}
          />
        )
      }
    >
      <Seo title={pageTitle("Build your plan")} description="Answer a few questions to build your plan." />
      <meta name="robots" content="noindex" />
      <div className={styles.page}>
        {checking ? (
          <p role="status" className={styles.body}>
            {QUIZ_UI.loading}
          </p>
        ) : (
          <>
            <img className={styles.image} src={waving} alt="" width={150} height={229} />
            <h1 className={styles.title} data-funnel-heading tabIndex={-1}>
              {QUIZ_INTRO.title}
            </h1>
            <p className={styles.body}>{QUIZ_INTRO.body}</p>
          </>
        )}
        {notice && !checking && (
          <p className={styles.notice} role="status">
            {RESTORE_FAILED}
          </p>
        )}
        {failure && (
          <div className={styles.error} role="alert">
            <p className={styles.errorText}>{ERROR_MESSAGES[failure.kind]}</p>
            <button
              type="button"
              className={styles.retry}
              onClick={() => {
                if (entry.status === "error") {
                  setEntry({ status: "checking" });
                  setAttempt((n) => n + 1);
                } else void start();
              }}
            >
              {QUIZ_UI.retry}
            </button>
          </div>
        )}
      </div>
    </FunnelScreen>
  );
}
