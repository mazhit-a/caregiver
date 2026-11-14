// Strings and limits of Mom's page that carry no placeholder. Names and labels with a recipient in
// them ("Mom's page", "About Mom") come from GET /app-copy. Wording here is typed for the content
// owner to review; nothing here is advice.
import type { Phrase } from "../../api/appTypes";

/** Mirrors backend/app/domain/profile/entities.py (locked by profile.test.ts). */
export const PROFILE_LIMITS = {
  displayName: 80,
  caregiverName: 40,
  listItems: 10,
  itemLength: 80,
  rhythmLength: 500,
  contacts: 5,
  contactName: 60,
  contactRole: 40,
  phoneLength: 30,
  phoneMinDigits: 7,
  phoneMaxDigits: 15,
} as const;

/** Same character rule as the server's `clean_phone`. */
export const PHONE_PATTERN = /^\+?[0-9 ()\-.]+$/;

export const PHRASE_SOURCE_LABEL: Record<Phrase["source"], string> = {
  scenario: "From a lesson",
  roleplay: "From practice",
  gift: "From your gift sheet",
};

export const PROFILE_TEXT = {
  edit: "Edit",
  loadingWhat: "profile",
  nameLabel: "Name or nickname",
  nameHint: "Only what you would call them. Leave it empty to use the default.",
  caregiverNameLabel: "Your first name (optional)",
  rhythmLabel: "Daily rhythm",
  rhythmHint: "For example: up at 7, tea at 10, quiet after 6.",
  addChip: "Add",
  chipPlaceholder: "Type and press Enter",
  chipsFull: "That is the most this list can hold.",
  chipTooLong: "That one is a little long. Please shorten it.",
  removeChip: "Remove",
  contactsAdd: "Add a contact",
  contactRemove: "Remove contact",
  contactName: "Name",
  contactPhone: "Phone",
  contactRole: "Role (optional)",
  contactNeedsBoth: "Add a name and a phone number, or remove this contact.",
  contactBadPhone: "That phone number doesn't look right. Use digits, spaces, dashes or +.",
  save: "Save",
  saving: "Saving...",
  cancel: "Cancel",
  discardTitle: "Leave without saving?",
  discardKeep: "Keep editing",
  discardLeave: "Leave without saving",
  saveFailed: "We couldn't save that. Please try again.",
  emptyChips: "Nothing here yet.",
  emptyRhythm: "Nothing here yet. Add the rhythm of a usual day.",
  emptyContacts: "No contacts yet. Add someone who can be called.",
  phrasesCopy: "Copy",
  phrasesCopied: "Copied",
  phrasesDelete: "Remove",
  deleteTitle: "Remove this phrase?",
  deleteBody: "It will no longer appear here or on a care card you update.",
  deleteConfirm: "Remove phrase",
  deleteKeep: "Keep it",
  deleteFailed: "We couldn't remove that phrase. Please try again.",
  phrasesEmptyAction: "Go to Today",
  phrasesLoadError: "We couldn't load your saved phrases.",
  careCardOpen: "Open the care card",
  visitOpen: "Open the visit sheet",
  visitTitle: "Next doctor visit",
  visitEmpty: "No visit planned yet. Add the date and your questions when you know them.",
  visitQuestionsOne: "1 question ready",
  visitQuestionsMany: (n: number): string => `${n} questions ready`,
  visitNoQuestions: "No questions yet",
} as const;
