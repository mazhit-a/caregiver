import { describe, expect, it } from "vitest";
import { GOAL_LABELS, HOME_ROUND, PRACTICE_SCRIPT, scoreOf, type PracticeRoundData } from "./practiceScript";

const allRounds: PracticeRoundData[] = [HOME_ROUND, ...Object.values(PRACTICE_SCRIPT).flat()];

describe("practiceScript", () => {
  it("scores by counting met goals", () => {
    expect(scoreOf({ goals: [false, false, false] })).toBe(0);
    expect(scoreOf({ goals: [false, true, false] })).toBe(1);
    expect(scoreOf({ goals: [true, true, true] })).toBe(3);
  });

  it("home round gives 0, 1 and 3 of 3", () => {
    expect(HOME_ROUND.options.map(scoreOf)).toEqual([0, 1, 3]);
  });

  it("each variant has 3 rounds with 3 options", () => {
    expect(Object.keys(PRACTICE_SCRIPT).sort()).toEqual(["in_person", "phone"]);
    for (const rounds of Object.values(PRACTICE_SCRIPT)) {
      expect(rounds).toHaveLength(3);
      for (const round of rounds) expect(round.options).toHaveLength(3);
    }
    expect(HOME_ROUND.options).toHaveLength(3);
  });

  it("every option has exactly 3 goal flags matching the labels", () => {
    expect(GOAL_LABELS).toHaveLength(3);
    for (const round of allRounds) {
      for (const option of round.options) expect(option.goals).toHaveLength(3);
    }
  });

  it("has no unfilled placeholder braces", () => {
    for (const round of allRounds) {
      const texts = [round.stage, round.line, ...round.options.flatMap((o) => [o.text, o.tip, o.mom])];
      for (const text of texts) expect(text).not.toMatch(/[{}]/);
    }
  });
});
