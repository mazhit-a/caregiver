import { describe, expect, it, vi } from "vitest";
import { buildIcs, downloadIcs, escapeIcsText, foldIcsLine, toIcsUtc } from "./ics";

const reminder = {
  title: "Your plan for next time",
  description: "If Mom calls, then I'll say: you're safe, I'm here.\nSave your phrase; copy it, too.",
  startsAt: "2026-01-05T19:00:00-05:00",
  timezone: "America/New_York",
  url: "http://localhost:3000/lessons/m1_l1",
};

describe("ics", () => {
  it("writes CRLF lines, a UTC start and no placeholders", () => {
    const text = buildIcs(reminder, "m1_l1");
    expect(text.endsWith("\r\n")).toBe(true);
    expect(text.split("\r\n").every((l) => !l.includes("\n"))).toBe(true);
    expect(text).toContain("DTSTART:20260106T000000Z");
    expect(text).toContain("DTEND:20260106T001500Z");
    expect(text).toContain("BEGIN:VEVENT");
    expect(text).not.toMatch(/\{/);
  });

  it("escapes commas, semicolons, backslashes and new lines", () => {
    expect(escapeIcsText("a,b;c\\d\ne")).toBe("a\\,b\\;c\\\\d\\ne");
    expect(buildIcs(reminder, "x")).toContain("copy it\\, too.");
  });

  it("folds long lines at 75 octets with a leading space", () => {
    const folded = foldIcsLine(`SUMMARY:${"a".repeat(200)}`).split("\r\n");
    expect(folded.length).toBeGreaterThan(2);
    expect(folded[0]).toHaveLength(75);
    expect(folded[1]?.startsWith(" ")).toBe(true);
    expect(folded.every((l) => new TextEncoder().encode(l).length <= 75)).toBe(true);
    expect(folded.join("").replace(/ /g, "")).toBe(`SUMMARY:${"a".repeat(200)}`);
  });

  it("rejects an unreadable time", () => {
    expect(() => toIcsUtc("tomorrow evening")).toThrow();
  });

  it("downloads once per call through an object URL", () => {
    const create = vi.fn(() => "blob:x");
    const revoke = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    downloadIcs("reminder.ics", "BEGIN:VCALENDAR");
    expect(create).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(revoke).toHaveBeenCalledWith("blob:x");
    click.mockRestore();
    vi.unstubAllGlobals();
  });
});
