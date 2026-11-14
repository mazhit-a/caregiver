/** Single list of routes (marketing site and funnel). */
export const ROUTES = {
  home: "/",
  how: "/how-it-works",
  practice: "/practice",
  course: "/course",
  tools: "/care-tools",
  pricing: "/pricing",
  quiz: "/quiz",
  quizBuilding: "/quiz/building",
  plan: "/your-plan",
  gift: "/your-plan/gift",
  paywall: "/paywall",
  checkoutReturn: "/checkout/return",
  today: "/today",
} as const;

/** One quiz step (a question id or a reassure_* screen id). An id is never an answer. */
export const quizQuestionRoute = (id: string): string =>
  `${ROUTES.quiz}/${encodeURIComponent(id)}`;
