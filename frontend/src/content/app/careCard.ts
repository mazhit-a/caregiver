// Strings of the care card owner screen that carry no placeholder. The title, purpose and the
// honest-sharing sentence come from GET /app-copy (careCard section). Nothing here is advice.
import type { CardStatus } from "../../api/appTypes";

/** Mirrors backend/app/domain/care_card (locked by careCard.test.ts). */
export const CARE_CARD_LIMITS = { phrases: 10 } as const;

export const CARD_STATUS_LABEL: Record<CardStatus, string> = {
  not_published: "Not shared yet",
  published: "Shared by link",
  update_available: "New phrases to add",
  revoked: "No longer shared",
};

export const CARE_CARD_TEXT = {
  loadingWhat: "care card",
  statusLabel: "Status",
  previewTitle: "Preview",
  previewNote: "This is what the link shows. Your phrase choices are added when you share or update.",
  enjoys: "Enjoys",
  calms: "Calms",
  avoid: "Try to avoid",
  rhythm: "Daily rhythm",
  contacts: "Contacts",
  helplines: "Helplines",
  phrases: "Phrases that work",
  updatedOn: "Updated",
  nothingYet: "Nothing added yet.",
  pickerTitle: "Phrases to include",
  pickerHint: "Choose up to 10, or none. You can change this any time.",
  pickerEmpty: "You have no saved phrases yet. You can share the card without any.",
  pickerCount: (n: number): string => `${n} of ${CARE_CARD_LIMITS.phrases} chosen`,
  pickerFull: "That is the most a card can hold.",
  publish: "Create private link",
  publishNew: "Create a new private link",
  publishing: "Creating link...",
  update: "Update the card",
  updating: "Updating...",
  newPhrasesOne: "1 saved phrase is not on the card yet.",
  newPhrasesMany: (n: number): string => `${n} saved phrases are not on the card yet.`,
  updateHint: "Your profile changed since you shared the card. Update it so the link shows what you see here.",
  revoke: "Stop sharing",
  revokeTitle: "Stop sharing this card?",
  revokeBody: "The link stops working right away for everyone who has it. You can create a new link later.",
  revokeKeep: "Keep sharing",
  revokeConfirm: "Stop sharing",
  revoked: "This link no longer works.",
  linkLabel: "Private link",
  copyLink: "Copy link",
  linkCopied: "Link copied",
  copyFallback: "Press Ctrl+C or Cmd+C to copy.",
  lastOpened: (date: string): string => `Last opened ${date}`,
  notOpened: "Not opened yet",
  print: "Print",
  printNote: "Prints only the card, on one page.",
  conflictAlready: "This card is already shared. We refreshed the page.",
  conflictNotShared: "This card is not shared right now. We refreshed the page.",
} as const;
