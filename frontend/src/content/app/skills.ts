// Placeholder-free wording for the Skills page. Titles and the item labels carry no name or
// pronoun on purpose, so nothing here needs the API's placeholder rendering.

export const SKILLS_COPY = {
  title: "Your skills",
  subtitle: "What you have practiced so far, from your lessons and practice rounds.",
  loading: "your skills",
  empty: "Practice in lesson 1 to see how your replies change.",
  practiceTitle: "Practice",
  noRounds: "No practice rounds yet.",
  scenariosNone: "No scenarios yet.",
  confidenceTitle: "How ready you felt",
  confidenceNote: "Your own ratings, from 1 to 5.",
  confidenceStart: "When you started",
  confidenceFirst: "After lesson 1",
  confidenceLatest: "Now",
  countsTitle: "So far",
  nextTitle: "Next",
  nextOpen: "Open lesson",
  limits: "This page shows only what you have done. It does not rate you.",
} as const;

/** Item ids of the wrap screen's confidence check (locked to content/lessons/m1_l1.json by the contract test). */
export const CONFIDENCE_LABELS: Record<string, string> = {
  repeat: "Repeated questions",
  accusations: "Thinking something was taken",
  evenings: "Upset evenings",
  refusal: "Saying no to help",
  visits: "Getting what you need from a doctor visit",
};

export const CONFIDENCE_ORDER = ["repeat", "accusations", "evenings", "refusal", "visits"] as const;

export const SKILLS_COUNT_LABELS = {
  scenariosPractised: "Scenarios practiced",
  phrasesSaved: "Phrases saved",
  tasksTried: "Real tasks tried",
  tasksHelped: "Tasks that helped",
} as const;

export const roleplayLine = (runs: number, first: number | null, latest: number | null, max: number): string => {
  if (runs === 0 || first === null || latest === null) return SKILLS_COPY.noRounds;
  const rounds = `${runs} ${runs === 1 ? "round" : "rounds"}`;
  if (runs === 1) return `First try: ${first} of ${max} (${rounds})`;
  return `First try: ${first} of ${max}. Latest: ${latest} of ${max} (${rounds})`;
};

export const scenarioLine = (practised: number, best: number): string =>
  practised === 0
    ? SKILLS_COPY.scenariosNone
    : `Best answer chosen in ${best} of ${practised} ${practised === 1 ? "scenario" : "scenarios"}`;

export const unlockLine = (date: string): string => `Opens ${date}`;
