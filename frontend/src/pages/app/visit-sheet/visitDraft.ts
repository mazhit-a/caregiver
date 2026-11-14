import type { VisitSheet, VisitSheetBody } from "../../../api/appTypes";
import { VISIT_LIMITS } from "../../../content/app/visit";

/** One row of the question list. `key` is stable for React; `id` is set for bank questions. */
export interface DraftQuestion {
  key: string;
  id: string | null;
  text: string;
}

export interface Draft {
  doctor: string;
  visitDate: string;
  familyNotes: string;
  questions: DraftQuestion[];
}

let counter = 0;
export const newKey = (): string => `q${(counter += 1)}`;

export function draftFrom(sheet: VisitSheet): Draft {
  return {
    doctor: sheet.doctor ?? "",
    visitDate: sheet.visitDate ?? "",
    familyNotes: sheet.familyNotes,
    questions: sheet.questions.map((q) => ({ key: newKey(), id: q.id, text: q.text })),
  };
}

/** The PUT body: `{id}` for bank questions, `{text}` for the family's own. Notes are sent as typed. */
export function toBody(draft: Draft): VisitSheetBody {
  return {
    doctor: draft.doctor.trim() === "" ? null : draft.doctor,
    visitDate: draft.visitDate === "" ? null : draft.visitDate,
    familyNotes: draft.familyNotes,
    questions: draft.questions.map((q) => (q.id !== null ? { id: q.id } : { text: q.text })),
  };
}

export function move<T>(items: readonly T[], from: number, to: number): T[] {
  if (to < 0 || to >= items.length) return [...items];
  const next = [...items];
  const [item] = next.splice(from, 1);
  if (item !== undefined) next.splice(to, 0, item);
  return next;
}

export const customCount = (questions: readonly DraftQuestion[]): number =>
  questions.filter((q) => q.id === null).length;

export type AddBlock = "total" | "custom" | null;

/** Why another question cannot be added right now (limits mirror the backend entity). */
export function addBlock(questions: readonly DraftQuestion[], custom: boolean): AddBlock {
  if (questions.length >= VISIT_LIMITS.questions) return "total";
  if (custom && customCount(questions) >= VISIT_LIMITS.customQuestions) return "custom";
  return null;
}

/** Appends a suggested note on its own line. Null when it would pass the length limit. */
export function appendNote(notes: string, text: string): string | null {
  const joined = notes.trim() === "" ? text : `${notes.replace(/\s+$/, "")}\n${text}`;
  return joined.length > VISIT_LIMITS.familyNotes ? null : joined;
}
