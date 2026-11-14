import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { APP_COMMON, APP_ERROR_MESSAGES } from "./common";

const copy = JSON.parse(
  readFileSync(resolve(process.cwd(), "../content/funnel-copy.json"), "utf-8"),
) as { common: Record<string, string> };

describe("shared app strings", () => {
  it("privacyShort mirrors content/funnel-copy.json", () => {
    expect(APP_COMMON.privacyShort).toBe(copy.common["privacyShort"]);
  });

  it("every failure kind has a warm line with no placeholder, no blame and no markup", () => {
    for (const [kind, message] of Object.entries(APP_ERROR_MESSAGES)) {
      expect(message.length, kind).toBeGreaterThan(10);
      expect(message, kind).not.toMatch(/[{}*]|you (failed|must)|wrong answer/i);
    }
    expect(Object.keys(APP_ERROR_MESSAGES)).toContain("billing_failed");
  });

  it("the billing failure never claims success", () => {
    expect(APP_ERROR_MESSAGES.billing_failed).toMatch(/nothing changed/i);
  });
});
