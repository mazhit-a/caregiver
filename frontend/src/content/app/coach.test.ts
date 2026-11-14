import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { COACH_COPY } from "./coach";

const root = resolve(__dirname, "../../../../content");

describe("coach copy", () => {
  it("mirrors the privacy line in content/funnel-copy.json", () => {
    const raw = readFileSync(resolve(root, "funnel-copy.json"), "utf8");
    expect(raw).toContain(COACH_COPY.privacyShort);
  });

  it("uses the goal labels of the lesson files", () => {
    const lesson = readFileSync(resolve(root, "lessons/m1_l2.json"), "utf8");
    for (const label of Object.values(COACH_COPY.goalLabels)) expect(lesson).toContain(label);
  });

  it("has no fear, sales or shaming words", () => {
    const text = JSON.stringify(COACH_COPY).toLowerCase();
    for (const banned of ["wrong", "per day", "hurry", "limited time", "discount"]) {
      expect(text).not.toContain(banned);
    }
  });
});

describe("coach copy (G8 additions)", () => {
  it("mirrors the aiDown line and the verdict labels of the lesson files", () => {
    const lesson = readFileSync(resolve(root, "lessons/m1_l1.json"), "utf8");
    expect(lesson).toContain(COACH_COPY.aiDown);
    for (const label of Object.values(COACH_COPY.verdictLabels)) expect(lesson).toContain(`"${label}"`);
  });

  it("has no unfilled placeholder and no countdown wording", () => {
    const text = JSON.stringify([
      COACH_COPY.crisisTitle,
      COACH_COPY.crisisBody,
      COACH_COPY.emergencyTitle,
      COACH_COPY.fallbackIntro,
    ]);
    expect(text).not.toContain("{");
    expect(text.toLowerCase()).not.toContain("countdown");
  });
});
