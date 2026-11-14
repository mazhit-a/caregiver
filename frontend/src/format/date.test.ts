import { afterEach, describe, expect, it } from "vitest";
import { formatDate } from "./date";

const originalTz = process.env["TZ"];
afterEach(() => {
  if (originalTz === undefined) delete process.env["TZ"];
  else process.env["TZ"] = originalTz;
});

describe("formatDate", () => {
  it("formats a date-only value as month and day", () => {
    expect(formatDate("2026-11-20")).toBe("Nov 20");
    expect(formatDate("2026-01-07")).toBe("Jan 7");
    expect(formatDate("2026-11-20", { year: true })).toBe("Nov 20, 2026");
  });

  it.each(["Etc/GMT+12", "Pacific/Kiritimati", "America/Los_Angeles", "Asia/Tokyo"])(
    "date-only never shifts a day in %s (UTC-12 and UTC+14 included)",
    (tz) => {
      process.env["TZ"] = tz;
      expect(formatDate("2026-03-01")).toBe("Mar 1");
      expect(formatDate("2026-12-31")).toBe("Dec 31");
    },
  );

  it("formats an instant in the browser time zone", () => {
    process.env["TZ"] = "America/New_York";
    expect(formatDate("2026-01-05T19:00:00-05:00")).toBe("Jan 5");
    expect(formatDate("2026-01-06T02:00:00Z")).toBe("Jan 5"); // 21:00 the evening before in New York
    process.env["TZ"] = "Asia/Tokyo";
    expect(formatDate("2026-01-06T02:00:00Z")).toBe("Jan 6");
  });

  it("returns an unparseable value unchanged and never reads the clock", () => {
    expect(formatDate("soon")).toBe("soon");
    expect(formatDate("2026-13-45")).toBe("2026-13-45");
  });
});
