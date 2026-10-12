export interface DurationCandidate { minutes: number; text: string; suggested: boolean }
/** Deliberately returns choices: app totals, weekly averages and chart axes are ambiguous. */
export function durationCandidates(text: string): DurationCandidate[] {
  const candidates: DurationCandidate[] = [];
  const unitHours = "(?:hours?|hrs?|h|год(?:ини|ин|ина)?|ч(?:ас(?:а|ов)?)?)";
  const unitMinutes = "(?:minutes?|mins?|m|хв(?:илин(?:и|а)?)?|мин(?:ут(?:ы|а)?)?)";
  const pattern = new RegExp(`(?:([0-9]{1,2})\\s*${unitHours}\\.?\\s*(?:([0-9]{1,2})\\s*${unitMinutes}\\.?)?|([0-9]{1,3})\\s*${unitMinutes}\\.?)`, "giu");
  for (const line of text.normalize("NFKC").split(/\r?\n/)) {
    for (const match of line.matchAll(pattern)) {
      // Avoid swallowing prefixes of words or numbers (e.g. 1500 minutes).
      const before = line.slice(0, match.index), after = line.slice((match.index ?? 0) + match[0].length);
      if (/[\p{L}\p{N}]$/u.test(before) || /^[\p{L}\p{N}]/u.test(after)) continue;
      const h = Number(match[1] ?? 0), m = Number(match[2] ?? match[3] ?? 0);
      const minutes = h * 60 + m;
      if (h > 24 || (match[1] && m >= 60) || minutes > 1440) continue;
      const suggested = /(?:total|screen time|екранн|усього|всього|загал|всего)/iu.test(line) &&
        !/(?:average|середн|средн|week|тижд|недел)/iu.test(line);
      const existing = candidates.find(c => c.minutes === minutes);
      if (existing) { existing.suggested ||= suggested; continue; }
      candidates.push({ minutes, text: line.trim().slice(0, 100), suggested });
    }
  }
  return candidates.sort((a, b) => Number(b.suggested) - Number(a.suggested)).slice(0, 15);
}
