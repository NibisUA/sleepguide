export const SCREEN_CATEGORIES = [
  { field: "social_minutes", color: "bg-sky-500", textColor: "text-sky-400" },
  { field: "entertainment_minutes", color: "bg-cyan-400", textColor: "text-cyan-400" },
  { field: "games_minutes", color: "bg-orange-400", textColor: "text-orange-400" },
] as const;
export type CategoryField = typeof SCREEN_CATEGORIES[number]["field"];
export type ScreenCategories = Partial<Record<CategoryField, number | null>>;

export function categoryDistribution(total: number, values: ScreenCategories) {
  const known = SCREEN_CATEGORIES.filter(({ field }) => values[field] != null);
  const sum = known.reduce((n, { field }) => n + (values[field] ?? 0), 0);
  const valid = Number.isFinite(total) && total >= 0 && total <= 1440 && known.every(({ field }) => Number.isInteger(values[field]) && (values[field] ?? 0) >= 0) && sum <= total;
  return { sum, remaining: total - sum, complete: known.length === SCREEN_CATEGORIES.length, valid };
}
