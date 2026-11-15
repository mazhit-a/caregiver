import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { PLAN_TEXT, doneOf, lessonsDoneOf, moduleKicker } from "./plan";

const rules = JSON.parse(
  readFileSync(resolve(process.cwd(), "../content/plan-rules.json"), "utf-8"),
) as { quickGuides: { id: string; title: string }[] };

describe("plan strings", () => {
  it("every plan quick guide id has a guide page in content/quick-guides.json (all chips link to /guides/<id>)", () => {
    const book = JSON.parse(readFileSync(resolve(process.cwd(), "../content/quick-guides.json"), "utf-8")) as {
      guides: { id: string }[];
    };
    const ids = book.guides.map((g) => g.id).sort();
    expect(rules.quickGuides.map((g) => g.id).sort()).toEqual(ids);
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
