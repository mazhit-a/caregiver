/** Plain shapes the coach components render (the room maps API data into these). */
export interface GoalState {
  key: string;
  label: string;
  met: boolean;
}
export interface CoachView {
  score: number;
  goals: GoalState[];
  tip: string;
  betterPhrase: string;
  parentReaction: string;
}
