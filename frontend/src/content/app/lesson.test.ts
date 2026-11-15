import { describe, expect, it } from "vitest";
import { LESSON_COPY } from "./lesson";

describe("lesson copy", () => {
  it("never labels an answer wrong and has no fear or sales words", () => {
    const text = JSON.stringify(LESSON_COPY).toLowerCase();
    for (const banned of ["wrong", "per day", "hurry", "limited time", "discount"]) {
      expect(text).not.toContain(banned);
    }
  });

  it("keeps the lesson-1 chrome strings: Start the lesson, Continue and the gate hints", () => {
    expect(LESSON_COPY.start).toBe("Start the lesson");
    expect(LESSON_COPY.next).toBe("Continue");
    expect(LESSON_COPY.gateHint.setup).toMatch(/choose an option/i);
    expect(LESSON_COPY.gateHint.answer).toMatch(/choose an answer/i);
  });
});
