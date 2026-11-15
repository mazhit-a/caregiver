// UI-owned strings of the public quick guide pages. Every guide word (titles, steps, the footer,
// section headings) comes from the API (content/quick-guides.json).

export const GUIDES_TEXT = {
  loading: "Loading the guide",
  back: "Back",
  logoLink: "Kelper home",
  helpSheetTitle: "Quick guides",
  retry: "Try again",
  notFound: { title: "We can't find this guide", body: "Check the link, or open another guide from the Plan page or the help button." },
  failed: { title: "We couldn't load this guide", body: "Check your connection and try again." },
  sourcesTitle: "Sources",
} as const;

export const guideRoute = (guideId: string): string => `/guides/${encodeURIComponent(guideId)}`;
