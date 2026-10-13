export interface DurationCandidate { minutes: number; text: string; suggested: boolean }
import type { CategoryField, ScreenCategories } from "./categories";

export interface OcrWord {
  text: string;
  confidence?: number;
  bbox: { x0: number; y0: number; x1: number; y1: number };
}
const categoryLabels: Record<CategoryField, RegExp> = {
  social_minutes: /\bSocial(?:\s+Networking)?\b|соцмережі|соціальні\s+мережі|соціальн[іа]/giu,
  entertainment_minutes: /\bEntertainment\b|розваги/giu,
  games_minutes: /\bGames\b|ігри/giu,
};
function categoryDurations(text: string) {
  // In the iOS widget's thin font, OCR can read "1h 13m" as "Th 13m".
  // Correct only an isolated hour token followed by numeric minutes.
  const corrected = text.replace(/(?<![\p{L}\p{N}])[IlT|]h(?=\s*\d{1,2}\s*(?:m|mins?|minutes?)\b)/gu, "1h");
  if (/(?<![\p{L}\p{N}])[a-z]+h\s*\d{1,2}\s*m\b/iu.test(corrected)) return [];
  return durationCandidates(corrected);
}

/** Read labelled values, including iOS widgets with category columns under a chart.
 * Ambiguous matches stay unknown; these are suggestions requiring explicit confirmation.
 */
export function categoryCandidates(text: string, words: OcrWord[] = []): ScreenCategories {
  const found = new Map<CategoryField, Set<number>>();
  function add(field: CategoryField, minutes: number) {
    const values = found.get(field) ?? new Set<number>();
    values.add(minutes); found.set(field, values);
  }
  const lines = text.normalize("NFKC").split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/(average|weekly|середн|тижд)/iu.test(line)) continue;
    const labels = Object.entries(categoryLabels).flatMap(([field, regex]) =>
      [...line.matchAll(new RegExp(regex.source, regex.flags))].map(match => ({ field: field as CategoryField, index: match.index ?? 0, end: (match.index ?? 0) + match[0].length })))
      .sort((a, b) => a.index - b.index);
    for (let j = 0; j < labels.length; j++) {
      const values = categoryDurations(line.slice(labels[j].end, labels[j + 1]?.index));
      if (values.length === 1) add(labels[j].field, values[0].minutes);
    }
    if (!words.length && labels.length && categoryDurations(line).length === 0 && lines[i + 1]) {
      const nextHasLabel = Object.values(categoryLabels).some(regex => { regex.lastIndex = 0; return regex.test(lines[i + 1]); });
      const values = categoryDurations(lines[i + 1]);
      if (!nextHasLabel && !/(average|weekly|середн|тижд)/iu.test(lines[i + 1]) && values.length === labels.length) {
        labels.forEach((label, index) => add(label.field, values[index].minutes));
      }
    }
  }
  const labels = words.flatMap(word => {
    if ((word.confidence ?? 100) < 45) return [];
    return Object.entries(categoryLabels).filter(([, regex]) => { regex.lastIndex = 0; return regex.test(word.text); })
      .map(([field]) => ({ field: field as CategoryField, word }));
  });
  for (const label of labels) {
    if (labels.filter(other => other.field === label.field).length !== 1) continue;
    const b = label.word.bbox, height = Math.max(1, b.y1 - b.y0), center = (b.x0 + b.x1) / 2;
    const row = labels.filter(other => Math.abs(other.word.bbox.y0 - b.y0) <= height).sort((a, c) => a.word.bbox.x0 - c.word.bbox.x0);
    const index = row.indexOf(label);
    const left = index > 0 ? (center + (row[index - 1].word.bbox.x0 + row[index - 1].word.bbox.x1) / 2) / 2 : b.x0 - height * 3;
    const right = index < row.length - 1 ? (center + (row[index + 1].word.bbox.x0 + row[index + 1].word.bbox.x1) / 2) / 2 : b.x1 + height * 6;
    const nearby = words.filter(word => {
      const x = (word.bbox.x0 + word.bbox.x1) / 2;
      return (word.confidence ?? 100) >= 35 && x >= left && x < right && word.bbox.y0 >= b.y0 - height * 0.2 && word.bbox.y1 <= b.y1 + height * 3;
    }).sort((a, c) => a.bbox.y0 - c.bbox.y0 || a.bbox.x0 - c.bbox.x0);
    const values = categoryDurations(nearby.map(word => word.text).join(" "));
    if (values.length === 1) add(label.field, values[0].minutes);
  }
  return Object.fromEntries([...found].filter(([, values]) => values.size === 1).map(([field, values]) => [field, [...values][0]]));
}
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
