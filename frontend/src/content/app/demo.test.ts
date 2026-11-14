import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { DEMO, DEMO_DONE_TEXT } from "./demo";
import { DEMO_ACTIONS } from "../../pages/app/today/demoActions";

const copy = JSON.parse(
  readFileSync(resolve(process.cwd(), "../content/funnel-copy.json"), "utf-8"),
) as { today: { demo: { label: string; controls: { id: string; label: string }[] } } };
const fixture = JSON.parse(
  readFileSync(resolve(process.cwd(), "src/test/fixtures/app/today-fresh.json"), "utf-8"),
) as { demo: { label: string; controls: { id: string; label: string }[] } };

describe("demo controls contract", () => {
  it("the action table covers exactly the control ids in funnel-copy.json", () => {
    expect(Object.keys(DEMO_ACTIONS).sort()).toEqual(copy.today.demo.controls.map((c) => c.id).sort());
    expect(Object.keys(DEMO_DONE_TEXT).sort()).toEqual(Object.keys(DEMO_ACTIONS).sort());
  });

  it("the API label and control labels are the content strings", () => {
    expect(fixture.demo.label).toBe(copy.today.demo.label);
    expect(fixture.demo.controls).toEqual(copy.today.demo.controls);
  });

  it("UI strings have no placeholder and no selling words", () => {
    for (const [key, value] of Object.entries(DEMO)) {
      expect(value, key).not.toMatch(/[{}]/);
      expect(value, key).not.toMatch(/per day|limited time|hurry|discount/i);
    }
  });
});
