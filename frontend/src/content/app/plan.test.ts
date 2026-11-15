import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { PLAN_TEXT, QG_LIMIT_ID, doneOf, lessonsDoneOf, moduleKicker } from "./plan";

const rules = JSON.parse(
  readFileSync(resolve(process.cwd(), "../content/plan-rules.json"), "utf-8"),
) as { quickGuides: { id: string; title: string }[] };

describe("plan strings", () => {
  it("the limit guide id exists in content/plan-rules.json", () => {
    const guide = rules.quickGuides.find((g) => g.id === QG_LIMIT_ID);
    expect(guide?.title).toMatch(/limit/i);
  });

  it("has no placeholder, countdown or fear wording", () => {
    const all = [...Object.values(PLAN_TEXT), moduleKicker(2, 3), doneOf(1, 5), lessonsDoneOf(1, 1)];
    for (const text of all) expect(text).not.toMatch(/[{}]|hurry|limited time|per day|don't miss/i);
  });

  it("counts read naturally", () => {
    expect(moduleKicker(1, 5)).toBe("Module 1 · 5 lessons");
    expect(lessonsDoneOf(0, 1)).toBe("0 of 1 lesson done");
  });
});
