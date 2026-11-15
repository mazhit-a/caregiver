// Visit sheet strings (G13). Placeholder-free: the page title and subtitle (which name the parent)
// come finished from GET /app-copy. Limits mirror backend/app/domain/visit_sheet/entities.py
// (locked by visit.test.ts). The footer is the server's, never written here.
export const VISIT_LIMITS = {
  doctor: 120,
  familyNotes: 2000,
  questions: 20,
  customQuestions: 10,
  customQuestionLength: 300,
} as const;

/** Wait after the last edit before saving. */
export const AUTOSAVE_MS = 800;

export const VISIT = {
  backToToday: "Back to Today",
  doctorLabel: "Doctor or clinic",
  dateLabel: "Visit date",
  notesTitle: "Notes from family, in your own words",
  notesHint: "We keep your words exactly as you write them.",
  suggestedTitle: "Things you noticed",
  suggestedHint: "From moments you chose to share. Add the ones you want to bring up.",
  addToNotes: "Add to notes",
  notesFull: "The notes are full. Make some room to add more.",
  questionsTitle: "Our questions",
  questionsEmpty: "No questions yet. Add some from the list or write your own.",
  moveUp: "Move up",
  moveDown: "Move down",
  remove: "Remove",
  bankTitle: "Add from the list",
  bankEmpty: "You have added every question from the list.",
  add: "Add",
  ownTitle: "Add your own",
  ownLabel: "Your question",
  ownAdd: "Add your question",
  tooManyQuestions: "The sheet holds up to 20 questions. Remove one to add another.",
  tooManyOwn: "You can add up to 10 questions of your own.",
  saving: "Saving...",
  saved: "Saved",
  notSaved: "Not saved yet.",
  saveRetry: "Try saving again",
  previewTitle: "Print preview",
  printButton: "Print or save as PDF",
  printHint: "Opens your device's print window. Choose Save as PDF to keep a copy.",
  sheetTitle: "Doctor visit sheet",
  preparedBy: "Prepared by",
  sheetDoctor: "Doctor",
  sheetDate: "Visit date",
  sheetNotes: "Notes from family",
  sheetQuestions: "Questions to ask",
  sheetAnswers: "Doctor's answers",
  sheetEmpty: "Nothing added yet.",
  loadingWhat: "visit sheet",
} as const;

/** Warm lines for the two 422 codes the visit sheet can return. Never echo the user's words. */
export const VISIT_VALIDATION_MESSAGES: Record<string, string> = {
  invalid_visit_sheet: "Something on the sheet is too long or empty. Please check it and try again.",
  unknown_visit_question: "One of the questions is no longer on the list. Please remove it and try again.",
};
