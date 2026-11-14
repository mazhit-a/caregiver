// UI-owned strings for the check-in and the welcome card. The question, options, answers and
// follow-up tips are finished text from the API; the welcome title/body/label come from app-copy.
// Nothing here has a placeholder.
export const CHECKIN = {
  heading: "Check-in",
  yourPlan: "Your plan",
  doctorNoteLabel: "Add to the doctor-visit sheet",
  doctorNoteField: "Your note (optional, up to 300 characters)",
  doctorNoteMax: 300,
  saving: "Saving your answer",
  alreadyAnswered: "Already answered",
  alreadyAnsweredHelp: "You answered this check-in earlier. We're refreshing your page.",
  addedToSheet: "Added to your doctor-visit sheet.",
  taskDone: "Marked as done in your plan.",
  followUpsHeading: "More ways to try",
  doneStatus: "Thanks. Your answer is saved.",
  loadingWhat: "check-in",
} as const;

export const WELCOME = {
  continue: "Continue",
  skip: "Skip",
  saving: "Saving",
  nameMax: 40,
  fallbackTitle: "Welcome",
  privacy: "Saved privately to this session. No account, no name needed.",
} as const;
