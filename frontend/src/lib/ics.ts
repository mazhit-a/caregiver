// Builds the "Remind me tomorrow" calendar file from the reminder the API returns.
// Pure text: it never reads the browser clock (DTSTAMP reuses the start time).

export interface Reminder {
  title: string;
  description: string;
  /** ISO instant with offset, e.g. `2026-01-05T19:00:00-05:00`. */
  startsAt: string;
  timezone: string;
  url: string;
}

const DURATION_MINUTES = 15;
const FOLD_AT = 75;

/** `20260106T000000Z` (UTC, as the file format wants it). */
export function toIcsUtc(instant: string): string {
  const date = new Date(instant);
  if (Number.isNaN(date.getTime())) throw new Error("invalid reminder time");
  return date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

export function escapeIcsText(text: string): string {
  return text
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r\n|\r|\n/g, "\\n");
}

/** Folds a content line at 75 octets, continuation lines start with one space. */
export function foldIcsLine(line: string): string {
  const encoder = new TextEncoder();
  const parts: string[] = [];
  let current = "";
  let size = 0;
  for (const char of line) {
    const bytes = encoder.encode(char).length;
    const limit = parts.length === 0 ? FOLD_AT : FOLD_AT - 1;
    if (size + bytes > limit) {
      parts.push(current);
      current = "";
      size = 0;
    }
    current += char;
    size += bytes;
  }
  parts.push(current);
  return parts.join("\r\n ");
}

export function buildIcs(reminder: Reminder, uidSeed: string): string {
  const start = toIcsUtc(reminder.startsAt);
  const end = toIcsUtc(
    new Date(new Date(reminder.startsAt).getTime() + DURATION_MINUTES * 60_000).toISOString(),
  );
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Parent Care Navigator//Reminder//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:${uidSeed}-${start}@parent-care-navigator`,
    `DTSTAMP:${start}`,
    `DTSTART:${start}`,
    `DTEND:${end}`,
    `SUMMARY:${escapeIcsText(reminder.title)}`,
    `DESCRIPTION:${escapeIcsText(reminder.description)}`,
    `URL:${reminder.url}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ];
  return lines.map(foldIcsLine).join("\r\n") + "\r\n";
}

/** Hands the file to the browser as a download. */
export function downloadIcs(fileName: string, ics: string): void {
  const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}
