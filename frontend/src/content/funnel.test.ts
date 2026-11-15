import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import * as F from "./funnel";

interface Copy {
  common: Record<string, string>;
  quizIntro: Record<string, string>;
  planPreview: {
    whatWeHeard: Record<string, string>;
    beforeAfter: Record<string, string>;
    plan: Record<string, string>;
    proof: { title: string; items: { text: string; source: string }[] };
    gift: Record<string, string>;
  };
  paywall: Record<string, string>;
  errors: Record<string, string>;
}
const raw = readFileSync(resolve(process.cwd(), "../content/funnel-copy.json"), "utf-8");
const c = JSON.parse(raw) as Copy;
const pp = c.planPreview;

describe("funnel copy mirrors content/funnel-copy.json", () => {
  it("common and quiz intro", () => {
    expect(F.COMMON).toEqual({
      privacyShort: c.common["privacyShort"],
      needHelpNow: c.common["needHelpNow"],
      back: c.common["back"],
      continue: c.common["continue"],
      skip: c.common["skip"],
    });
    expect(F.QUIZ_INTRO).toEqual(c.quizIntro);
  });

  it("plan preview labels", () => {
    expect(F.PLAN_PREVIEW).toEqual({
      whatWeHeardTitle: pp.whatWeHeard["title"],
      editLink: pp.whatWeHeard["editLink"],
      beforeAfterTitle: pp.beforeAfter["title"],
      beforeLabel: pp.beforeAfter["beforeLabel"],
      afterLabel: pp.beforeAfter["afterLabel"],
      first30Title: pp.plan["first30Title"],
      laterTitle: pp.plan["laterTitle"],
      quickGuidesTitle: pp.plan["quickGuidesTitle"],
      quickGuidesNote: pp.plan["quickGuidesNote"],
      reasonPrefix: pp.plan["reasonPrefix"],
    });
    expect(F.moduleLessonsLabel(4)).toBe(pp.plan["moduleLessonsLabel"]?.replace("{count}", "4"));
    expect(F.paceLine(3)).toBe(pp.plan["paceLine"]?.replace("{perWeek}", "3"));
  });

  it("gift, proof", () => {
    expect(F.GIFT_CARD).toEqual({
      title: pp.gift["title"],
      cta: pp.gift["cta"],
      note: pp.gift["note"],
    });
    expect(F.PROOF.title).toBe(pp.proof.title);
    expect(F.PROOF.items).toEqual(pp.proof.items);
  });

  it("paywall static strings and errors", () => {
    expect(F.PAYWALL).toEqual({
      includesTitle: c.paywall["includesTitle"],
      testModeHint: c.paywall["testModeHint"],
      demoButton: c.paywall["demoButton"],
      demoNote: c.paywall["demoNote"],
      footer: c.paywall["footer"],
      loading: (c.paywall["states"] as unknown as Record<string, string>)["loading"],
      cardError: (c.paywall["states"] as unknown as Record<string, string>)["cardError"],
    });
    expect(F.RESTORE_FAILED).toBe(c.errors["restoreFailed"]);
    expect(F.ERROR_MESSAGES.unknown).toBe(c.errors["generic"]);
  });
});

describe("funnel module hygiene", () => {
  const strings: string[] = [];
  const walk = (v: unknown): void => {
    if (typeof v === "string") strings.push(v);
    else if (typeof v === "function") strings.push(String(v(3)));
    else if (Array.isArray(v)) v.forEach(walk);
    else if (typeof v === "object" && v !== null) Object.values(v).forEach(walk);
  };
  Object.values(F).forEach(walk);

  it("has no browser-storage wording, placeholders, per-day prices or countdowns", () => {
    expect(strings.length).toBeGreaterThan(40);
    for (const s of strings) {
      expect(s).not.toMatch(/in this browser|your browser/i);
      expect(s).not.toMatch(/[{}]/);
      expect(s).not.toMatch(/per day|a day\b|\/day/i);
      expect(s).not.toMatch(/countdown|hurry|expires|only \d+ left|last chance/i);
    }
  });

  it("has a message for every failure kind", () => {
    for (const msg of Object.values(F.ERROR_MESSAGES)) expect(msg.length).toBeGreaterThan(10);
  });
});
