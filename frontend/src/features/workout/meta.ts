import type { WorkoutIntensity, WorkoutType } from "../../types/api";

export const WORKOUT_TYPES: readonly WorkoutType[] = [
  "gym",
  "home",
  "running",
  "football",
  "walking",
  "other",
];

export const WORKOUT_INTENSITIES: readonly WorkoutIntensity[] = [
  "easy",
  "moderate",
  "hard",
  "very_hard",
];

export const TYPE_ICON: Record<WorkoutType, string> = {
  gym: "🏋️",
  home: "🏠",
  running: "🏃",
  football: "⚽",
  walking: "🚶",
  other: "✨",
};

export const DEFAULT_TYPE: WorkoutType = "gym";
export const DEFAULT_INTENSITY: WorkoutIntensity = "moderate";

/** A workout running longer than this needs its end time confirmed (matches the backend). */
export const FORGOTTEN_WORKOUT_MINUTES = 6 * 60;

/** Tailwind text color per intensity. */
export const INTENSITY_COLOR: Record<WorkoutIntensity, string> = {
  easy: "text-muted",
  moderate: "text-primary",
  hard: "text-warning",
  very_hard: "text-danger",
};
