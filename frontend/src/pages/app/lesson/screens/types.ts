import type { ComponentType } from "react";
import type { KnownScreen, Lesson } from "../../../../api/appTypes";

/** What a screen remembers while the learner moves Back and Next (in memory only). */
export interface AnswerEntry {
  value: string;
  result: Record<string, unknown>;
  /** Scenario answer ids whose phrase was saved. */
  saved: string[];
}
export type AnswerStore = Record<string, AnswerEntry>;

export interface ScreenProps<S> {
  screen: S;
  lesson: Lesson;
  entry: AnswerEntry | undefined;
  /** Every screen's remembered answer, by screen id (the plan screen reads the role-play result). */
  answers?: AnswerStore;
  remember: (screenId: string, next: (previous: AnswerEntry | undefined) => AnswerEntry) => void;
  /** Re-fetches the lesson without leaving the player; resolves true when it worked. */
  reload: () => Promise<boolean>;
}

export type ScreenRegistry = {
  [K in KnownScreen["type"]]: ComponentType<ScreenProps<Extract<KnownScreen, { type: K }>>>;
};
