import { describe, expect, it } from "vitest";
import { EXIT, exitTexts, isGoodbyeState } from "./exit";
import { BANNED } from "./settings.test";

describe("exit wording", () => {
  it("has no retention, offer or fear copy", () => {
    for (const text of exitTexts()) for (const rule of BANNED) expect(text).not.toMatch(rule);
    for (const text of exitTexts()) expect(text).not.toMatch(/\{|\}/);
  });
  it("states the facts and the failure honestly", () => {
    expect(EXIT.step1Facts.join(" ")).toMatch(/cannot be undone/);
    expect(EXIT.blocked).toMatch(/nothing was deleted/);
  });
  it("guards router state", () => {
    expect(isGoodbyeState(null)).toBe(false);
    expect(isGoodbyeState({ kind: "cleared", message: "x" })).toBe(true);
    expect(isGoodbyeState({ kind: "exit", title: "t", condolence: "c", resources: [] })).toBe(true);
    expect(isGoodbyeState({ kind: "exit" })).toBe(false);
  });
});
