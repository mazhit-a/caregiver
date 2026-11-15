import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { LESSON_COPY } from "./lesson";

describe("lesson copy", () => {
  it("mirrors the not-medical-advice line in content/funnel-copy.json", () => {
    const raw = readFileSync(resolve(__dirname, "../../../../content/funnel-copy.json"), "utf8");
    const copy = JSON.parse(raw) as { common: { notMedicalAdvice?: string } };
    if (copy.common.notMedicalAdvice) {
      expect(copy.common.notMedicalAdvice.replace(/’/g, "'")).toBe(
        LESSON_COPY.notMedicalAdvice.replace(/’/g, "'"),
      );
    } else {
      expect(raw.replace(/’/g, "'")).toContain(LESSON_COPY.notMedicalAdvice.replace(/’/g, "'"));
    }
  });

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
