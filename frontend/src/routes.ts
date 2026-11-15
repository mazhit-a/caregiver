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
  fakeCheckout: "/fake-checkout/:checkoutId",
  today: "/today",
  // The app after the paywall (batch 3). `plan` above is the funnel's "/your-plan".
  todayPractice: "/today/practice",
  lesson: "/lessons/:lessonId",
  appPlan: "/plan",
  profile: "/profile",
  careCard: "/care-card",
  visitSheet: "/visit-sheet",
  skills: "/skills",
  settings: "/settings",
  settingsCancel: "/settings/cancel",
  settingsGentleExit: "/settings/gentle-exit",
  goodbye: "/goodbye",
  card: "/card/:cardId",
} as const;

/** One lesson player route. */
export const lessonRoute = (lessonId: string): string =>
  `/lessons/${encodeURIComponent(lessonId)}`;

/** The public care card page (a bearer link; never put it in a title or history on the owner side). */
export const cardRoute = (cardId: string): string =>
  `/card/${encodeURIComponent(cardId)}`;

/** One quiz step (a question id or a reassure_* screen id). An id is never an answer. */
export const quizQuestionRoute = (id: string): string =>
  `${ROUTES.quiz}/${encodeURIComponent(id)}`;
