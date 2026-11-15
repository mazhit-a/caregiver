import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  CANCEL,
  DEMO_CONTROL_LABELS,
  SETTINGS,
  STATUS_LABELS,
  cancelFacts,
  canceledText,
  isCancellable,
  statusText,
} from "./settings";

export const BANNED = [
  /per day/i,
  /\/day/i,
  /limited time/i,
  /hurry/i,
  /don't miss/i,
  /are you sure you want to leave/i,
  /we'll miss you/i,
  /special offer/i,
  /discount/i,
  /survey/i,
  /stay with us/i,
];

const funnel = JSON.parse(readFileSync(resolve(process.cwd(), "../content/funnel-copy.json"), "utf-8")) as {
  common: Record<string, string>;
};
const STATUSES = ["demo", "active", "canceling", "past_due", "canceled", "ended", "none"];

function allText(): string[] {
  return [
    ...Object.values(SETTINGS),
    ...Object.values(CANCEL),
    ...Object.values(STATUS_LABELS),
    ...Object.values(DEMO_CONTROL_LABELS),
    ...STATUSES.flatMap((s) => [statusText(s, "Mar 2, 2026"), statusText(s, null)]),
    cancelFacts({ planName: "4 weeks", savedPhraseCount: 2, careCardPublished: true, endDate: "Mar 2, 2026" }),
    cancelFacts({ planName: "4 weeks", savedPhraseCount: 0, careCardPublished: false, endDate: null }),
    canceledText("Mar 2, 2026"),
    canceledText(null),
  ];
}

describe("settings wording", () => {
  it("the section heading is exactly Subscription (the paywall says so)", () => {
    expect(SETTINGS.subscriptionTitle).toBe("Subscription");
    expect(funnel.common).toBeDefined();
    const copy = readFileSync(resolve(process.cwd(), "../content/funnel-copy.json"), "utf-8");
    expect(copy).toContain("Settings → Subscription");
  });

  it("the privacy line mirrors funnel-copy", () => {
    expect(SETTINGS.privacyNote).toBe(funnel.common["privacyShort"]);
  });

  it("has no placeholder, markup or banned phrase", () => {
    for (const text of allText()) {
      expect(text).not.toMatch(/[{}*]|undefined|null/);
      for (const rule of BANNED) expect(text).not.toMatch(rule);
    }
  });

  it("every status has a sentence and the right cancel rule", () => {
    for (const status of STATUSES) expect(statusText(status, null).length).toBeGreaterThan(10);
    expect(STATUSES.filter(isCancellable)).toEqual(["demo", "active", "past_due"]);
  });

  it("the facts sentence drops what the API did not send", () => {
    const withCard = cancelFacts({ planName: "4 weeks", savedPhraseCount: 1, careCardPublished: true, endDate: "Mar 2, 2026" });
    expect(withCard).toBe(
      "If you cancel, you keep full access until Mar 2, 2026. After that you'll lose access to 4 weeks, 1 saved phrase and your care card link.",
    );
    const bare = cancelFacts({ planName: "4 weeks", savedPhraseCount: 2, careCardPublished: false, endDate: null });
    expect(bare).toBe("If you cancel, you'll lose access to 4 weeks and 2 saved phrases.");
  });
});
