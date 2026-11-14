import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { COURSE_MODULES, MODULE_ONE, QUICK_GUIDES } from "./course";

interface RuleLesson {
  title: string;
  minutes: number;
  built: boolean;
}
interface RuleModule {
  id: string;
  title: string;
  lessons: RuleLesson[];
}
interface Rules {
  modules: RuleModule[];
  quickGuides: { id: string; title: string }[];
}

const rules = JSON.parse(readFileSync(resolve(process.cwd(), "../content/plan-rules.json"), "utf-8")) as Rules;

const LABELS: Record<string, string> = {
  "{recipient}": "Mom",
  "{Recipient}": "Mom",
  "{possessive}": "Mom’s",
  "{pronoun}": "she",
};

/** Renders placeholders for Mom and normalises straight quotes to the typographic ones used on the page. */
function render(text: string): string {
  const filled = text.replace(/\{\w+\}/g, (key) => LABELS[key] ?? key);
  return filled.replace(/'/g, "’").replace(/"([^"]*)"/g, "“$1”");
}

function ruleModule(id: string): RuleModule {
  const found = rules.modules.find((m) => m.id === id);
  if (!found) throw new Error(`plan-rules.json has no module ${id}`);
  return found;
}

describe("course page content matches content/plan-rules.json", () => {
  it("lists the eight modules after Module 1 in plan-rules order", () => {
    expect(COURSE_MODULES).toHaveLength(8);
    expect(COURSE_MODULES.map((m) => m.id)).toEqual(rules.modules.slice(1).map((m) => m.id));
  });

  it("matches module titles, lesson titles and minutes", () => {
    for (const module of COURSE_MODULES) {
      const source = ruleModule(module.id);
      expect(module.title).toBe(render(source.title));
      expect(module.lessons.map((l) => l.title)).toEqual(source.lessons.map((l) => render(l.title)));
      expect(module.lessons.map((l) => l.minutes)).toEqual(source.lessons.map((l) => l.minutes));
    }
  });

  it("states lesson counts that match, unless the module is marked coming later", () => {
    for (const module of COURSE_MODULES) {
      const n = ruleModule(module.id).lessons.length;
      if (module.count === "Coming later") continue;
      expect(module.count).toBe(`${n} lessons`);
    }
  });

  it("marks a module built only when every lesson is built in plan-rules", () => {
    for (const module of COURSE_MODULES) {
      const allBuilt = ruleModule(module.id).lessons.every((l) => l.built);
      expect(module.built).toBe(allBuilt);
      expect(Boolean(module.badge) || module.built || module.count === "Coming later").toBe(true);
    }
  });

  it("matches Module 1 lessons and the five quick guide titles", () => {
    const m1 = ruleModule("m1_talking");
    expect(MODULE_ONE.lessons.map((l) => l.title)).toEqual(m1.lessons.map((l) => render(l.title)));
    expect(MODULE_ONE.lessons.map((l) => l.minutes)).toEqual(m1.lessons.map((l) => l.minutes));
    expect(QUICK_GUIDES.items.map((g) => g.title)).toEqual(rules.quickGuides.map((g) => render(g.title)));
  });
});
