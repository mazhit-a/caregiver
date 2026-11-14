import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router";
import { clearToken, getToken } from "../../api/session";
import type { ApiFailure } from "../../api/errors";
import type { AnswerValue, QuizQuestion, QuizState } from "../../api/funnelTypes";
import { ActionBar } from "../../components/funnel/ActionBar";
import { DocumentGrid } from "../../components/funnel/DocumentGrid";
import { Interstitial } from "../../components/funnel/Interstitial";
import { MultiChoice } from "../../components/funnel/MultiChoice";
import { ProgressBar } from "../../components/funnel/ProgressBar";
import { QuestionFrame } from "../../components/funnel/QuestionFrame";
import { ScaleInput } from "../../components/funnel/ScaleInput";
import { SingleChoice } from "../../components/funnel/SingleChoice";
import { COMMON, ERROR_MESSAGES } from "../../content/funnel";
import { FunnelScreen } from "../../layout/funnel/FunnelScreen";
import { Seo, pageTitle } from "../../layout/Seo";
import { quizQuestionRoute, ROUTES } from "../../routes";
import { QUIZ_HEALTH_NOTE, QUIZ_UI } from "./quizCopy";
import { answerableCount, failureRoute, isComplete, progressNumber, resumeIndex } from "./quizSteps";
import { useQuiz } from "./useQuiz";
import styles from "./quiz.module.css";

type Draft = AnswerValue | null;

function initialDraft(question: QuizQuestion, saved: AnswerValue | undefined): Draft {
  if (saved !== undefined) return saved;
  if (question.type === "multi") return [];
  if (question.type === "grid") return {};
  return null;
}

interface StepProps {
  quiz: QuizState;
  index: number;
  saveAnswer: ReturnType<typeof useQuiz>["saveAnswer"];
  onFailure: (failure: ApiFailure) => string | null;
}

/** One screen. Keyed by question id, so the draft starts from the saved answer on every step. */
function Step({ quiz, index, saveAnswer, onFailure }: StepProps) {
  const navigate = useNavigate();
  const question = quiz.questions[index] as QuizQuestion;
  const [draft, setDraft] = useState<Draft>(() => initialDraft(question, quiz.answers[question.id]));
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<ApiFailure | null>(null);

  const previous = quiz.questions[index - 1];
  const next = quiz.questions[index + 1];
  const nextRoute = next ? quizQuestionRoute(next.id) : ROUTES.quizBuilding;
  const total = answerableCount(quiz);
  const number = progressNumber(quiz, index);
  const label = QUIZ_UI.progressLabel(number, total);
  const interstitial = question.type === "interstitial";

  const save = async (value: AnswerValue) => {
    if (saving) return;
    setSaving(true);
    setFailure(null);
    const result = await saveAnswer(question.id, value);
    setSaving(false);
    if (result.ok) navigate(nextRoute);
    else {
      const route = onFailure(result.failure);
      if (route) navigate(route, { replace: true, state: route === ROUTES.quiz ? { restore: true } : null });
      else setFailure(result.failure);
    }
  };

  const onContinue = () => {
    if (interstitial) navigate(nextRoute);
    else if (draft !== null) void save(draft);
  };

  const disabled = saving || (!interstitial && !isComplete(question, draft));
  const skippable = question.type === "multi" && question.skippable === true;
  const healthNote = question.healthData ? QUIZ_HEALTH_NOTE : undefined;

  let body;
  switch (question.type) {
    case "single":
      body = (
        <SingleChoice
          legend={question.title}
          options={question.options}
          value={typeof draft === "string" ? draft : null}
          onChange={setDraft}
        />
      );
      break;
    case "multi":
      body = (
        <MultiChoice
          legend={question.title}
          options={question.options}
          max={question.max}
          value={Array.isArray(draft) ? draft : []}
          onChange={setDraft}
        />
      );
      break;
    case "grid":
      body = (
        <DocumentGrid
          rows={question.rows}
          states={question.states}
          value={typeof draft === "object" && draft !== null && !Array.isArray(draft) ? draft : {}}
          onChange={setDraft}
        />
      );
      break;
    case "scale":
      body = (
        <ScaleInput
          legend={question.title}
          min={question.min}
          max={question.max}
          minLabel={question.minLabel}
          maxLabel={question.maxLabel}
          value={typeof draft === "number" ? draft : null}
          onChange={setDraft}
        />
      );
      break;
    default:
      body = null;
  }

  return (
    <FunnelScreen
      back={{ to: previous ? quizQuestionRoute(previous.id) : ROUTES.quiz }}
      progress={<ProgressBar current={number} total={total} label={label} />}
      actionBar={
        <ActionBar
          primary={{
            label: interstitial ? question.cta : saving ? QUIZ_UI.saving : COMMON.continue,
            disabled,
            onClick: onContinue,
          }}
          secondary={skippable ? { label: COMMON.skip, onClick: () => void save([]) } : undefined}
        />
      }
    >
      <Seo title={pageTitle(`Question ${number} of ${total}`)} description="Kelper quiz." />
      <meta name="robots" content="noindex" />
      {question.type === "interstitial" ? (
        <Interstitial title={question.title} body={question.body} />
      ) : (
        <QuestionFrame title={question.title} subtitle={question.subtitle} healthNote={healthNote}>
          {body}
        </QuestionFrame>
      )}
      {failure && (
        <div className={styles.error} role="alert">
          <p className={styles.errorText}>{ERROR_MESSAGES[failure.kind]}</p>
        </div>
      )}
    </FunnelScreen>
  );
}

/** `/quiz/:questionId`: one question per route, so Back and reload both work. */
export default function QuizStepPage() {
  const { questionId } = useParams();
  const { load, refresh, saveAnswer } = useQuiz();

  const onFailure = (failure: ApiFailure): string | null => {
    if (failure.kind === "session_lost") {
      clearToken();
      return ROUTES.quiz;
    }
    return failureRoute(failure);
  };

  useEffect(() => {
    if (load.status === "error" && load.failure.kind === "session_lost") clearToken();
  }, [load]);

  if (!getToken() && load.status !== "ready") return <Navigate to={ROUTES.quiz} replace />;

  if (load.status === "error") {
    const route = onFailure(load.failure);
    if (route) {
      return (
        <Navigate
          to={route}
          replace
          state={route === ROUTES.quiz ? { restore: true } : null}
        />
      );
    }
    return (
      <FunnelScreen back={{ to: ROUTES.quiz }}>
        <Seo title={pageTitle("Quiz")} description="Kelper quiz." />
        <meta name="robots" content="noindex" />
        <div className={styles.error} role="alert">
          <p className={styles.errorText}>{ERROR_MESSAGES[load.failure.kind]}</p>
          <button type="button" className={styles.retry} onClick={refresh}>
            {QUIZ_UI.retry}
          </button>
        </div>
      </FunnelScreen>
    );
  }

  if (load.status === "loading") {
    return (
      <FunnelScreen back={{ to: ROUTES.quiz }}>
        <Seo title={pageTitle("Quiz")} description="Kelper quiz." />
        <meta name="robots" content="noindex" />
        <p role="status" className={styles.body}>
          {QUIZ_UI.loading}
        </p>
      </FunnelScreen>
    );
  }

  const { quiz } = load;
  if (quiz.locked) return <Navigate to={ROUTES.today} replace />;
  const index = quiz.questions.findIndex((q) => q.id === questionId);
  const allowed = resumeIndex(quiz);
  const target = quiz.questions[allowed];
  if ((index === -1 || index > allowed) && target) {
    return <Navigate to={quizQuestionRoute(target.id)} replace />;
  }
  return (
    <Step
      key={questionId}
      quiz={quiz}
      index={index}
      saveAnswer={saveAnswer}
      onFailure={onFailure}
    />
  );
}
