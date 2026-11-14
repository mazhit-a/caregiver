import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { APP_COMMON } from "./common";
import { VISIT, VISIT_LIMITS, VISIT_VALIDATION_MESSAGES } from "./visit";

const entities = readFileSync(
  resolve(process.cwd(), "../backend/app/domain/visit_sheet/entities.py"),
  "utf-8",
);
const limit = (name: string): number => {
  const match = new RegExp(`${name} = (\\d+)`).exec(entities);
  if (!match) throw new Error(`${name} not found`);
  return Number(match[1]);
};

describe("visit sheet limits mirror the backend entity", () => {
  it("every limit equals domain/visit_sheet/entities.py", () => {
    expect(VISIT_LIMITS.doctor).toBe(limit("MAX_DOCTOR_LENGTH"));
    expect(VISIT_LIMITS.familyNotes).toBe(limit("MAX_FAMILY_NOTES_LENGTH"));
    expect(VISIT_LIMITS.questions).toBe(limit("MAX_QUESTIONS"));
    expect(VISIT_LIMITS.customQuestions).toBe(limit("MAX_CUSTOM_QUESTIONS"));
    expect(VISIT_LIMITS.customQuestionLength).toBe(limit("MAX_CUSTOM_QUESTION_LENGTH"));
  });
});

describe("visit sheet strings", () => {
  it("have no placeholder, no medical advice, no pressure", () => {
    const all = [...Object.values(VISIT), ...Object.values(VISIT_VALIDATION_MESSAGES)].join(" ");
    expect(all).not.toMatch(/[{}]/);
    expect(all).not.toMatch(/\b(diagnos|dose|medication|you must|hurry|only \d+ left)/i);
  });

  it("the privacy line is the shared one", () => {
    expect(APP_COMMON.privacyShort).toBe("Saved privately to this session. No account, no name needed.");
  });
});
