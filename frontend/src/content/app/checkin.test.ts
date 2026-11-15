import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { CHECKIN, WELCOME } from "./checkin";

const read = (p: string) => JSON.parse(readFileSync(resolve(process.cwd(), p), "utf-8")) as never;
const lesson = read("../content/lessons/m1_l1.json") as { day2: { doctorNote: { button: string } } };
const appCopy = read("../content/app-copy.json") as {
  profile: { privacyNote: string };
};

describe("check-in strings", () => {
  it("the doctor-note label is the lesson's own button text", () => {
    expect(CHECKIN.doctorNoteLabel).toBe(lesson.day2.doctorNote.button);
  });
  it("the privacy line is the one in app-copy", () => {
    expect(WELCOME.privacy).toBe(appCopy.profile.privacyNote);
  });
  it("have no placeholder and no banned selling words", () => {
    for (const [key, value] of Object.entries({ ...CHECKIN, ...WELCOME })) {
      if (typeof value !== "string") continue;
      expect(value, key).not.toMatch(/[{}]/);
      expect(value, key).not.toMatch(/per day|\/day|limited time|hurry|don't miss|special offer|discount/i);
    }
  });
});
