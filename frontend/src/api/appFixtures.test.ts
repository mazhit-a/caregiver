import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { appFixture } from "../test/fakeApp/fixtures";
import { isKnownScreen, toScreen } from "./app";
import * as T from "./appTypes";
import { SUBSCRIPTION_KEYS } from "./funnelTypes";

/** Sorted keys equal sorted key list: a field added or removed on either side fails here. */
function expectKeys(value: unknown, keys: readonly string[]): void {
  expect(Object.keys(value as object).sort()).toEqual([...keys].sort());
}

const names = (re: RegExp): string[] =>
  readdirSync(resolve(process.cwd(), "src/test/fixtures/app"))
    .map((f) => f.replace(/\.json$/, ""))
    .filter((n) => re.test(n));

const f = appFixture;
type Rec = Record<string, unknown>;

describe("app fixtures (captured from the real backend) match the hand-written types", () => {
  it("app-copy", () => {
    const copy = f<Rec>("app-copy");
    expectKeys(copy, T.APP_COPY_KEYS);
    expect(Object.keys(copy["nav"] as Rec).sort()).toEqual(
      ["plan", "profilePage", "settings", "skills", "today"],
    );
  });

  it.each(names(/^today-/))("%s", (name) => {
    const today = f<Rec>(name);
    expectKeys(today, T.TODAY_KEYS);
    const next = today["nextStep"] as { lesson: Rec | null };
    if (next.lesson) expectKeys(next.lesson, T.TODAY_LESSON_KEYS);
    if (today["checkIn"]) expectKeys(today["checkIn"], T.CHECKIN_CARD_KEYS);
    if (today["practiceRound"]) expectKeys(today["practiceRound"], T.PRACTICE_ROUND_KEYS);
  });

  it("plan", () => {
    expectKeys(f("plan"), T.COURSE_PLAN_KEYS);
    expectKeys(f("plan-all-done"), T.COURSE_PLAN_KEYS);
  });

  it.each(names(/^lesson-/).filter((n) => !n.endsWith("initial")))("%s", (name) => {
    const lesson = f<{ screens: Rec[] } & Rec>(name);
    expectKeys(lesson, T.LESSON_KEYS);
    expectKeys(lesson["progress"], T.LESSON_PROGRESS_KEYS);
    for (const screen of lesson.screens) expect(isKnownScreen(screen)).toBe(true);
  });

  it("answers per screen type", () => {
    for (const n of names(/^answer-/)) expectKeys(f(n), T.ANSWER_RESULT_KEYS);
    expectKeys((f<Rec>("answer-scenario-a1")["result"]), T.SCENARIO_RESULT_KEYS);
    expectKeys((f<Rec>("answer-plan")["result"]), T.PLAN_RESULT_KEYS);
    expectKeys((f<Rec>("answer-wrap")["result"]), T.WRAP_RESULT_KEYS);
    expectKeys(f<Rec>("answer-setup-both")["result"], ["variant"]);
    expectKeys(f<Rec>("answer-minitask-main")["result"], ["optionId", "response"]);
  });

  it("complete, progress", () => {
    expectKeys(f("complete"), T.LESSON_COMPLETE_KEYS);
    expectKeys(f("complete-last"), T.LESSON_COMPLETE_KEYS);
    expectKeys(f("progress-put"), T.LESSON_PROGRESS_KEYS);
  });

  it.each(names(/^roleplay-start-/))("%s", (name) => expectKeys(f(name), T.ROLEPLAY_START_KEYS));

  it.each(names(/^roleplay-turn-/))("%s", (name) => {
    const turn = f<Rec>(name);
    expectKeys(turn, T.ROLEPLAY_TURN_KEYS);
    if (turn["coach"]) expectKeys(turn["coach"], T.COACH_PANEL_KEYS);
  });

  it.each(names(/^roleplay-finish-/))("%s", (name) => expectKeys(f(name), T.ROLEPLAY_FINISH_KEYS));

  it("covers every role-play mode", () => {
    expect(f<Rec>("roleplay-turn-ai-1")["mode"]).toBe("ai");
    expect(f<Rec>("roleplay-turn-medical-1")["coach"]).toMatchObject({ flags: ["medical"], score: 0 });
    expect(f<Rec>("roleplay-turn-fallback-1")["mode"]).toBe("fallback");
    expect(f<Rec>("roleplay-turn-crisis-1")).toMatchObject({ mode: "safety", kind: "crisis" });
    expect(f<Rec>("roleplay-turn-emergency-1")).toMatchObject({ mode: "safety", kind: "emergency" });
  });

  it("phrases, check-ins, skills", () => {
    expectKeys(f("phrase-saved"), T.PHRASE_KEYS);
    expectKeys((f<{ phrases: Rec[] }>("phrases-one")).phrases[0], T.PHRASE_KEYS);
    expectKeys(f("phrases-empty"), ["phrases"]);
    expectKeys(f("checkin-helped"), T.CHECKIN_RESULT_KEYS);
    expectKeys(f("checkin-didnt-help"), T.CHECKIN_RESULT_KEYS);
    for (const n of names(/^skills-/)) expectKeys(f(n), T.SKILLS_KEYS);
  });

  it("profile, care card, public card, visit sheet", () => {
    for (const n of names(/^profile-/)) expectKeys(f(n), T.PROFILE_KEYS);
    for (const n of names(/^care-card-/)) {
      const card = f<Rec>(n);
      expectKeys(card, T.CARE_CARD_KEYS);
      expectKeys(card["preview"], T.CARD_SNAPSHOT_KEYS);
    }
    expectKeys(f("card-public"), T.CARD_SNAPSHOT_KEYS);
    for (const n of names(/^visit-sheet-/)) expectKeys(f(n), T.VISIT_SHEET_KEYS);
  });

  it("covers the four care card statuses", () => {
    const statuses = names(/^care-card-/).map((n) => f<{ status: string }>(n).status);
    expect(statuses.sort()).toEqual(["not_published", "published", "revoked", "update_available"]);
  });

  it("billing, exit, demo", () => {
    for (const n of names(/^subscription-/)) expectKeys(f(n), SUBSCRIPTION_KEYS);
    expectKeys(f("cancel-preview"), T.CANCEL_PREVIEW_KEYS);
    expectKeys(f("cancel"), T.CANCEL_RESULT_KEYS);
    expectKeys(f("exit-gentle"), T.GENTLE_EXIT_KEYS);
    expectKeys(f("clear-data"), ["message"]);
    for (const n of ["demo", "demo-next-day", "demo-jump-to-renewal"]) expectKeys(f(n), T.DEMO_KEYS);
  });

  it("errors use the shared shape", () => {
    for (const n of names(/^err-|^demo-fail/)) {
      const body = f<{ error: Rec }>(n);
      expectKeys(body, ["error"]);
      expectKeys(body.error, ["code", "message", "details"]);
    }
  });

  it("carries the three lesson variants and the unrendered-placeholder check (flag 13)", () => {
    expect(names(/^lesson-m1_l1-(in_person|both|not_yet|phone-main)$/)).toHaveLength(4);
    expect(f<Rec>("lesson-m1_l2")["id"]).toBe("m1_l2");
    expect(f<Rec>("lesson-m1_l5")["id"]).toBe("m1_l5");
  });

  it("no fixture holds an unfilled {placeholder} or a session token", () => {
    const dir = resolve(process.cwd(), "src/test/fixtures/app");
    for (const file of readdirSync(dir)) {
      const text = readFileSync(resolve(dir, file), "utf-8");
      expect(text, file).not.toMatch(/\{[A-Za-z]+\}/);
      expect(text, file).not.toMatch(/X-Session-Token|fake-token/);
    }
    // The care card link is redacted: only the placeholder id remains.
    expect(readFileSync(resolve(dir, "care-card-published.json"), "utf-8")).toContain("REDACTED_CARD_ID");
  });
});

describe("screen guard", () => {
  it("accepts all 7 screen types found in the captured lessons", () => {
    const seen = new Set<string>();
    for (const n of names(/^lesson-/)) {
      for (const screen of f<{ screens: Rec[] }>(n).screens) {
        expect(isKnownScreen(screen), `${n} ${String(screen["id"])}`).toBe(true);
        seen.add(String(screen["type"]));
      }
    }
    expect([...seen].sort()).toEqual([...T.SCREEN_TYPES].sort());
  });

  it("turns an unknown or malformed screen into a typed unknown state", () => {
    expect(toScreen({ id: "x1", type: "hologram", text: "?" })).toEqual({ id: "x1", type: "unknown" });
    expect(toScreen({ id: "x2", type: "scenario" })).toEqual({ id: "x2", type: "unknown" });
    expect(toScreen(null)).toEqual({ id: "unknown", type: "unknown" });
    expect(isKnownScreen({ id: "x", type: "hologram" })).toBe(false);
  });
});
