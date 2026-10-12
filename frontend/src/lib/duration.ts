/** Hours + minutes <-> total minutes, for the "5 h 18 m" style used by iOS Screen Time. */

export function splitMinutes(total: number | null): { hours: string; minutes: string } {
  if (total === null) return { hours: "", minutes: "" };
  return { hours: String(Math.floor(total / 60)), minutes: String(total % 60) };
}

/**
 * Both empty -> null (not entered). Otherwise a whole number of minutes, or NaN when the input is
 * not a valid non-negative integer / minutes are 60 or more.
 */
export function joinMinutes(hours: string, minutes: string): number | null {
  if (hours.trim() === "" && minutes.trim() === "") return null;
  const h = hours.trim() === "" ? 0 : Number(hours);
  const m = minutes.trim() === "" ? 0 : Number(minutes);
  if (!Number.isInteger(h) || !Number.isInteger(m) || h < 0 || m < 0 || m >= 60) return Number.NaN;
  return h * 60 + m;
}
