import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { TODAY } from "./today";

const copy = JSON.parse(
  readFileSync(resolve(process.cwd(), "../content/funnel-copy.json"), "utf-8"),
) as { today: { visitSheetLink: string } };
const fixture = JSON.parse(
  readFileSync(resolve(process.cwd(), "src/test/fixtures/app/today-fresh.json"), "utf-8"),
) as { visitSheetLink: { label: string } };

describe("Today strings", () => {
  it("the visit sheet label served by the API is the content string", () => {
    expect(fixture.visitSheetLink.label).toBe(copy.today.visitSheetLink);
  });

  it("have no placeholder and none of the banned selling words", () => {
    for (const [key, value] of Object.entries(TODAY)) {
      expect(value, key).not.toMatch(/[{}]/);
      expect(value, key).not.toMatch(/per day|\/day|limited time|hurry|don't miss|special offer|discount/i);
    }
  });
});
