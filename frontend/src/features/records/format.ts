import type { TFunction } from "i18next";
import { formatClock } from "../../lib/format";
import type { ExerciseLog, Record } from "../../types/api";

export function numeric(value: number, locale: string) {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value);
}
export function logText(log: Pick<ExerciseLog, "weight_kg" | "reps" | "distance_m" | "duration_seconds">, t: TFunction, locale: string) {
  if (log.reps !== null) return t("records.strengthResult", { kg: numeric(log.weight_kg ?? 0, locale), reps: log.reps });
  const distance = t("records.meters", { n: numeric(log.distance_m ?? 0, locale) });
  return log.duration_seconds !== null ? `${distance} · ${formatClock(log.duration_seconds)}` : distance;
}
export function recordText(record: Record, t: TFunction, locale: string) {
  if (record.metric === "time") return `${formatClock(record.value)} · ${t("records.meters", { n: numeric(record.distance_m ?? 0, locale) })}`;
  if (record.metric === "distance") return t("records.meters", { n: numeric(record.value, locale) });
  if (record.metric === "reps") return t("records.repetitions", { n: numeric(record.value, locale) });
  return t("records.kilograms", { n: numeric(record.value, locale) });
}
