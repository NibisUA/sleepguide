import type { SleepDay } from "../types/api";

/** Color band shared by the score ring, score numbers and heatmap cells. */
export function scoreColor(score: number): string {
  if (score >= 85) return "text-primary";
  if (score >= 70) return "text-warning";
  return "text-danger";
}

/** Fill for the yearly heatmap: brighter green for better-scored nights. */
export function heatmapColor(day: SleepDay): string {
  if (day.score !== null) {
    const alpha = 0.25 + 0.75 * (Math.min(Math.max(day.score, 0), 100) / 100);
    return `rgba(33, 216, 144, ${alpha.toFixed(2)})`;
  }
  if (day.nap_minutes > 0) return "rgba(229, 166, 58, 0.45)"; // nap-only day
  return "rgba(113, 129, 122, 0.12)"; // no data
}
