import { SaveTemplate } from "../workout/Templates";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { QueryError, Skeleton } from "../../components/QueryState";
import { PrimaryButton } from "../../components/ui";
import { WriteError } from "./WriteError";
import { confirmAction } from "../../lib/confirm";
import { formatDate } from "../../lib/format";
import type { components } from "../../types/api.gen";
import type { Exercise, ExerciseLog, Workout } from "../../types/api";
import { useCreateExercise, useDeleteLog, useExerciseLogs, useExercises, useSaveLog, useSaveSets } from "./api";
import { logText } from "./format";

const inputClass = "mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text";
export { WriteError } from "./WriteError";

export function ExerciseLogsSheet({ workout, onClose }: { workout: Workout; onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const exercises = useExercises(), logs = useExerciseLogs(workout.id);
  const create = useCreateExercise(), save = useSaveLog(workout.id), remove = useDeleteLog();
  const batch = useSaveSets(workout.id);
  const [setCount, setSetCount] = useState("1");
  const [selected, setSelected] = useState("");
  const [newExercise, setNewExercise] = useState(false);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<Exercise["kind"]>("strength");
  const [editing, setEditing] = useState<ExerciseLog | null>(null);
  const [weight, setWeight] = useState(""), [reps, setReps] = useState("");
  const [distance, setDistance] = useState("");
  const [minutes, setMinutes] = useState(""), [seconds, setSeconds] = useState("");
  const busy = create.isPending || save.isPending || remove.isPending || batch.isPending;
  const exercise = exercises.data?.find(row => String(row.id) === selected);

  function clear() { setEditing(null); setWeight(""); setReps(""); setDistance(""); setMinutes(""); setSeconds(""); setSetCount("1"); save.reset(); batch.reset(); }
  function edit(log: ExerciseLog) {
    setNewExercise(false); setEditing(log); setSelected(String(log.exercise_id));
    setWeight(log.weight_kg === null ? "" : String(log.weight_kg)); setReps(log.reps === null ? "" : String(log.reps));
    setDistance(log.distance_m === null ? "" : String(log.distance_m));
    setMinutes(log.duration_seconds === null ? "" : String(Math.floor(log.duration_seconds / 60)));
    setSeconds(log.duration_seconds === null ? "" : String(log.duration_seconds % 60)); save.reset();
  }
  function usePlan(item: components["schemas"]["ExerciseLogCreateIn-Output"]) {
    clear(); setNewExercise(false); setSelected(String(item.exercise_id));
    setWeight(item.weight_kg == null ? "" : String(item.weight_kg)); setReps(item.reps == null ? "" : String(item.reps));
    setDistance(item.distance_m == null ? "" : String(item.distance_m));
    setMinutes(item.duration_seconds == null ? "" : String(Math.floor(item.duration_seconds / 60)));
    setSeconds(item.duration_seconds == null ? "" : String(item.duration_seconds % 60));
  }
  return <Modal title={t("records.resultsTitle")} onClose={() => { if (!busy) onClose(); }}>
    <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold">{t("records.resultsTitle")}</h2>
      <button type="button" disabled={busy} onClick={onClose} className="min-h-11 text-primary">{t("day.close")}</button></div>
    <p className="mt-1 text-sm text-muted">{formatDate(workout.local_date, i18n.language)} · {t(`workout.types.${workout.type}`)}</p>
    <p className="mt-2 text-sm text-muted">{t("records.resultsHint")}</p>
    {exercises.isPending || logs.isPending ? <Skeleton /> : exercises.isError || logs.isError ?
      <QueryError error={exercises.error ?? logs.error} retry={() => { void exercises.refetch(); void logs.refetch(); }} /> : <>
      {(workout.planned_sets?.length ?? 0) > 0 && <details open className="mt-3 rounded-xl bg-bg p-3">
        <summary className="font-medium">{t("templates.planTitle")}</summary><p className="mt-1 text-xs text-muted">{t("templates.planHint")}</p>
        <ol className="mt-2 divide-y divide-muted/20">{workout.planned_sets?.map((item, index) => <li key={index} className="py-2">
          <p className="text-sm">{index + 1}. {exercises.data.find(row => row.id === item.exercise_id)?.name ?? t("templates.missing")}</p>
          <p className="mt-1 text-xs text-muted">{logText({ ...item, weight_kg: item.weight_kg == null ? null : Number(item.weight_kg), reps: item.reps ?? null, distance_m: item.distance_m ?? null, duration_seconds: item.duration_seconds ?? null }, t, i18n.language)}</p>
          <button type="button" disabled={busy || !exercises.data.some(row => row.id === item.exercise_id)} onClick={() => usePlan(item)} className="min-h-11 text-sm text-primary">{t("templates.useTarget")}</button>
        </li>)}</ol>
      </details>}
      {workout.ended_at && !!logs.data?.length && <SaveTemplate workout={workout} />}
      {logs.data?.length ? <ul className="mt-4 divide-y divide-muted/20">{logs.data.map((log, index) => <li key={log.id} className="py-3">
        <p className="break-words text-sm font-medium">{exercises.data.find(row => row.id === log.exercise_id)?.name}</p>
        <p className="mt-1 text-sm text-muted">{logText(log, t, i18n.language)}</p>
        {log.reps !== null && <p className="mt-1 text-xs text-muted">{t("records.setNumber", { n: logs.data.slice(0, index + 1).filter(row => row.exercise_id === log.exercise_id).length })}</p>}
        {log.reps !== null && logs.data.find(row => row.exercise_id === log.exercise_id)?.id === log.id && <p className="mt-1 text-xs text-muted">{t("records.setSummary", { count: logs.data.filter(row => row.exercise_id === log.exercise_id).length, volume: new Intl.NumberFormat(i18n.language).format(logs.data.filter(row => row.exercise_id === log.exercise_id).reduce((sum, row) => sum + (row.weight_kg ?? 0) * (row.reps ?? 0), 0)) })}</p>}
        <div className="mt-1 flex gap-5 text-sm"><button type="button" disabled={busy} className="min-h-11 text-primary" onClick={() => edit(log)}>{t("workout.edit")}</button>
          <button type="button" disabled={busy} className="min-h-11 text-danger" onClick={async () => {
            if (await confirmAction(t("records.deleteLogConfirm"))) remove.mutate(log.id, { onSuccess: () => { if (editing?.id === log.id) clear(); } });
          }}>{t("workout.delete")}</button></div>
      </li>)}</ul> : <p className="mt-4 text-sm text-muted">{t("records.noResults")}</p>}
      <WriteError error={remove.error} />
      {!newExercise && <form className="mt-4 border-t border-muted/20 pt-4" onSubmit={event => {
        event.preventDefault(); if (!exercise || busy) return;
        const values = { id: editing?.id, exercise_id: exercise.id,
          ...(exercise.kind === "strength" ? { weight_kg: weight, reps: Number(reps) }
            : { distance_m: Number(distance), duration_seconds: minutes || seconds ? Number(minutes || 0) * 60 + Number(seconds || 0) : null }) };
        if (!editing && exercise.kind === "strength" && Number(setCount) > 1) {
          batch.mutate(Array.from({ length: Number(setCount) }, () => ({ ...values, id: undefined })), { onSuccess: clear });
        } else save.mutate(values, { onSuccess: clear });
      }}>
        <h3 className="font-medium">{editing ? t("records.editResult") : t("records.addResult")}</h3>
        <label className="mt-3 block text-sm text-muted">{t("records.exercise")}
          <select required value={selected} disabled={busy || !!editing} onChange={event => { setSelected(event.target.value); clear(); }} className={inputClass}>
            <option value="">{t("records.choose")}</option>{exercises.data.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}
          </select></label>
        {!editing && <button type="button" disabled={busy} className="mt-2 min-h-11 text-sm text-primary" onClick={() => { setNewExercise(true); create.reset(); }}>{t("records.newExercise")}</button>}
        {exercise?.kind === "strength" && <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="text-sm text-muted">{t("records.weight")}<input type="number" inputMode="decimal" required min="0" max="2000" step="0.01" value={weight} disabled={busy} onChange={e => setWeight(e.target.value)} className={inputClass} /></label>
          <label className="text-sm text-muted">{t("records.reps")}<input type="number" inputMode="numeric" required min="1" max="1000" step="1" value={reps} disabled={busy} onChange={e => setReps(e.target.value)} className={inputClass} /></label>
          <p className="col-span-2 text-xs text-muted">{t("records.bodyweight")}</p>
          {!editing && <label className="col-span-2 text-sm text-muted">{t("records.setCount")}<input aria-label={t("records.setCount")} type="number" required min="1" max="20" step="1" value={setCount} disabled={busy} onChange={e => setSetCount(e.target.value)} className={inputClass} /><span className="mt-1 block text-xs">{t("records.repeatHint")}</span></label>}
        </div>}
        {exercise?.kind === "cardio" && <>
          <label className="mt-3 block text-sm text-muted">{t("records.distance")}<input type="number" inputMode="numeric" required min="1" max="1000000" step="1" value={distance} disabled={busy} onChange={e => setDistance(e.target.value)} className={inputClass} /></label>
          <p className="mt-3 text-sm text-muted">{t("records.optionalTime")}</p>
          <div className="mt-1 grid grid-cols-2 gap-3"><label className="text-sm text-muted">{t("records.minutes")}<input type="number" inputMode="numeric" min="0" max="360" step="1" value={minutes} disabled={busy} onChange={e => setMinutes(e.target.value)} className={inputClass} /></label>
            <label className="text-sm text-muted">{t("records.seconds")}<input type="number" inputMode="numeric" min="0" max="59" step="1" value={seconds} disabled={busy} onChange={e => setSeconds(e.target.value)} className={inputClass} /></label></div>
        </>}
        <WriteError error={save.error ?? batch.error} />
        <PrimaryButton type="submit" disabled={!exercise || busy}>{busy ? t("common.loading") : t("records.saveResult")}</PrimaryButton>
        {editing && <button type="button" disabled={busy} onClick={clear} className="mt-2 min-h-11 text-muted">{t("common.cancel")}</button>}
      </form>}
      {newExercise && <form className="mt-4 border-t border-muted/20 pt-4" onSubmit={event => {
        event.preventDefault(); if (busy) return; create.mutate({ name, kind }, { onSuccess: row => { setSelected(String(row.id)); setNewExercise(false); setName(""); clear(); } });
      }}><h3 className="font-medium">{t("records.newExercise")}</h3>
        <label className="mt-3 block text-sm text-muted">{t("records.name")}<input required maxLength={80} value={name} disabled={busy} onChange={event => setName(event.target.value)} className={inputClass} /></label>
        <label className="mt-3 block text-sm text-muted">{t("records.kind")}<select value={kind} disabled={busy} onChange={event => setKind(event.target.value as Exercise["kind"])} className={inputClass}>
          <option value="strength">{t("records.strength")}</option><option value="cardio">{t("records.cardio")}</option></select></label>
        <p className="mt-2 text-xs text-muted">{t("records.kindHint")}</p><WriteError error={create.error} />
        <PrimaryButton type="submit" disabled={busy || !name.trim()}>{t("records.createExercise")}</PrimaryButton>
        <button type="button" disabled={busy} onClick={() => setNewExercise(false)} className="mt-2 min-h-11 text-muted">{t("common.cancel")}</button>
      </form>}
    </>}
  </Modal>;
}
