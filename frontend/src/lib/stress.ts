import type { StressCategory, StressLevel } from "../types/api";

export const STRESS_LEVELS: readonly StressLevel[] = [1, 2, 3, 4, 5];

export const STRESS_CATEGORIES: readonly StressCategory[] = [
  "university",
  "work",
  "relationships",
  "money",
  "sleep",
  "training",
  "personal",
  "other",
];

type Tone = "low" | "mid" | "high";

/** Green below 2.5, amber up to 3.5, red above. Works for single ratings and for averages. */
export function stressTone(value: number): Tone {
  if (value < 2.5) return "low";
  if (value < 3.5) return "mid";
  return "high";
}

const TEXT: Record<Tone, string> = {
  low: "text-primary",
  mid: "text-warning",
  high: "text-danger",
};
const FILL: Record<Tone, string> = {
  low: "fill-primary",
  mid: "fill-warning",
  high: "fill-danger",
};
const SOFT_BG: Record<Tone, string> = {
  low: "bg-primary/15 text-primary",
  mid: "bg-warning/15 text-warning",
  high: "bg-danger/15 text-danger",
};

export const stressTextClass = (value: number) => TEXT[stressTone(value)];
export const stressFillClass = (value: number) => FILL[stressTone(value)];
export const stressSoftClass = (value: number) => SOFT_BG[stressTone(value)];
