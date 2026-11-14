import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { DO_NOW_ACTIONS, IF_THEN_RESPONSE_MAX, PLAN_SCREEN_COPY, WRAP_COPY } from "./planScreen";

const root = join(__dirname, "../../../..");
const read = (p: string): string => readFileSync(join(root, p), "utf8");

describe("plan screen copy", () => {
  it("mirrors the domain constants", () => {
    const py = read("backend/app/domain/lessons/plans.py");
    expect(py).toContain(`IF_THEN_RESPONSE_MAX = ${IF_THEN_RESPONSE_MAX}`);
  });

  it("handles every doNow action used by the lesson files", () => {
    const dir = join(root, "content/lessons");
    const used = new Set<string>();
    for (const file of readdirSync(dir).filter((f) => f.endsWith(".json"))) {
      const lesson = JSON.parse(read(`content/lessons/${file}`)) as {
        screens: { type: string; doNow?: { byVariant: Record<string, { action: string }> } }[];
      };
      for (const s of lesson.screens)
        if (s.type === "plan" && s.doNow)
          for (const v of Object.values(s.doNow.byVariant)) used.add(v.action);
    }
    expect(used.size).toBeGreaterThan(0);
    for (const action of used) expect(DO_NOW_ACTIONS).toContain(action);
  });

  it("carries no placeholder braces, no medical advice words and no fear copy", () => {
    const text = JSON.stringify([PLAN_SCREEN_COPY.required, WRAP_COPY.heading, PLAN_SCREEN_COPY.saved]);
    expect(text).not.toMatch(/[{}]/);
    expect(PLAN_SCREEN_COPY.savedPrivately).toBe(
      "Saved privately to this session. No account, no name needed.",
    );
  });
});
