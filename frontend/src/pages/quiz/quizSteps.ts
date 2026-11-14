import { type ApiFailure, gateRoute } from "../../api/errors";
import type { QuizQuestion, QuizState } from "../../api/funnelTypes";
import { ROUTES } from "../../routes";

/** Pure helpers over the API's question list. No question ids are hard-coded. */
export const isAnswerable = (q: QuizQuestion): boolean => q.type !== "interstitial";

export function answerableCount(quiz: QuizState): number {
  return quiz.questions.filter(isAnswerable).length;
}

/** Index of the first unanswered question; the last step when everything is answered. */
export function resumeIndex(quiz: QuizState): number {
  const i = quiz.questions.findIndex((q) => isAnswerable(q) && quiz.answers[q.id] === undefined);
  return i === -1 ? Math.max(quiz.questions.length - 1, 0) : i;
}

/** "N of 11": interstitials show the number of the question before them. */
export function progressNumber(quiz: QuizState, index: number): number {
  return quiz.questions.slice(0, index + 1).filter(isAnswerable).length;
}

export function isComplete(question: QuizQuestion, value: unknown): boolean {
  switch (question.type) {
    case "single":
      return typeof value === "string";
    case "multi":
      return Array.isArray(value) && value.length > 0;
    case "scale":
      return typeof value === "number";
    case "grid": {
      const map = typeof value === "object" && value !== null ? (value as Record<string, unknown>) : {};
      return question.rows.every((r) => typeof map[r.id] === "string");
    }
    default:
      return true;
  }
}

/** Where a failed request sends the user, or null when the page should show a message. */
export function failureRoute(failure: ApiFailure): string | null {
  if (failure.kind === "locked") return ROUTES.today;
  if (failure.kind === "gate") return gateRoute(failure.reason).path;
  return null;
}
