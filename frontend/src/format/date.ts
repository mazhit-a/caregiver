/**
 * Display-only date formatting ("Nov 20"). The one allowed formatter in the browser.
 * It never reads the browser clock and never computes "tomorrow" or "in 2 days".
 */

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

export interface DateFormatOptions {
  /** Adds the year ("Nov 20, 2026"). */
  year?: boolean;
}

/**
 * A date-only value (`2026-11-20`) is parsed as y-m-d and formatted in UTC, so no time zone can
 * shift the day. An instant (`2026-11-20T19:00:00-05:00`) is formatted in the browser time zone,
 * which is the zone the session was created with. Anything unparseable comes back unchanged.
 */
export function formatDate(value: string, options: DateFormatOptions = {}): string {
  const format = (timeZone?: string): Intl.DateTimeFormat =>
    new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      ...(options.year ? { year: "numeric" } : {}),
      ...(timeZone ? { timeZone } : {}),
    });
  const dateOnly = DATE_ONLY.exec(value);
  if (dateOnly) {
    const [, y, m, d] = dateOnly;
    const date = new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
    // Reject overflow such as month 13 or day 45 (Date.UTC would roll it over silently).
    const valid =
      date.getUTCFullYear() === Number(y) &&
      date.getUTCMonth() === Number(m) - 1 &&
      date.getUTCDate() === Number(d);
    return valid ? format("UTC").format(date) : value;
  }
  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) return value;
  return format().format(instant);
}
