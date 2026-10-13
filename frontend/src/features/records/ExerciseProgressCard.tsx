import { useState } from "react";
import { useTranslation } from "react-i18next";
import { formatDate } from "../../lib/format";
import type { ExerciseRecords, Record } from "../../types/api";
import { logText, numeric, recordText } from "./format";

export function ExerciseProgressCard({ data, onOpen, children }: { data: ExerciseRecords; onOpen: (id: number) => void; children: React.ReactNode }) {
  const { t, i18n } = useTranslation();
  const { exercise, records } = data;
  const repBests = [...(data.rep_bests ?? [])].sort((a, b) => (b.weight_kg ?? 0) - (a.weight_kg ?? 0));
  const [weight, setWeight] = useState<number | null>(null);
  const selected = repBests.find(row => row.weight_kg === weight) ?? repBests[0];
  const strength = exercise.kind === "strength";
  const main = records.find(row => row.metric === (strength ? "weight" : "distance"));
  const times = records.filter(row => row.metric === "time");
  function result(record: Record, title: string) {
    return <div key={`${record.metric}-${record.weight_kg}-${record.distance_m}`} className="mt-3 rounded-xl bg-surface p-3">
      <p className="text-xs text-muted">{title}</p>
      <p className="mt-1 text-xl font-semibold text-primary">{strength ? logText(record, t, i18n.language) : recordText(record, t, i18n.language)}</p>
      <button type="button" onClick={() => onOpen(record.workout_id)} className="mt-2 min-h-11 text-xs text-primary">
        {formatDate(record.date, i18n.language, { day: "numeric", month: "short", year: "numeric" })} · {t("records.openWorkout")}
      </button>
    </div>;
  }
  return <article className="mt-4 rounded-2xl bg-bg p-4">
    <h3 className="break-words font-semibold">{exercise.name}</h3>
    <p className="mt-1 text-xs text-muted">{t(strength ? "records.strength" : "records.cardio")}</p>
    {!records.length && <p className="mt-3 text-sm text-muted">{t("records.noResults")}</p>}
    {main && result(main, t(strength ? "records.bestSet" : "records.longestDistance"))}
    {strength && selected && <div className="mt-3">
      <label className="block text-sm text-muted">{t("records.compareWeight")}
        <select value={selected.weight_kg ?? 0} onChange={e => setWeight(Number(e.target.value))} className="mt-1 w-full rounded-xl border border-muted/30 bg-surface p-3 text-text">
          {repBests.map(row => <option key={row.weight_kg} value={row.weight_kg ?? 0}>{row.weight_kg === 0 ? t("records.bodyweightLabel") : t("records.kilograms", { n: numeric(row.weight_kg ?? 0, i18n.language) })}</option>)}
        </select>
      </label>
      {result(selected, t("records.bestRepsAtWeight"))}
      <p className="mt-2 text-xs text-muted">{t("records.fairComparison")}</p>
    </div>}
    {!strength && times.map(record => result(record,
      t("records.fastestAtDistance", { distance: t("records.meters", { n: numeric(record.distance_m ?? 0, i18n.language) }) })
    ))}
    {!!records.length && <details className="mt-3 text-sm"><summary className="cursor-pointer py-2 text-muted">{t("records.details")}</summary>
      {records.filter(row => row.metric === "set_volume" || row.metric === "reps").map(record => <div key={record.metric} className="mt-2">
        <p>{t(`records.metrics.${record.metric}`)}: {recordText(record, t, i18n.language)}</p>
        <p className="mt-1 text-xs text-muted">{logText(record, t, i18n.language)}</p>
      </div>)}
      <p className="mt-2 text-xs text-muted">{t("records.volumeExplanation")}</p>
    </details>}
    <details className="mt-3 text-sm"><summary className="cursor-pointer py-2 text-muted">{t("records.manageExercise")}</summary>{children}</details>
  </article>;
}
