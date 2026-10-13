import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { Modal } from "../../components/Modal";
import { QueryError, Skeleton } from "../../components/QueryState";
import { PrimaryButton } from "../../components/ui";
import { confirmAction } from "../../lib/confirm";
import { api } from "../../lib/api";
import type { Exercise, Workout } from "../../types/api";
import { useDeleteExercise, useRecords, useRenameExercise } from "./api";
import { ExerciseLogsSheet, WriteError } from "./ExerciseLogsSheet";
import { ExerciseProgressCard } from "./ExerciseProgressCard";

export function RecordsSection() {
  const { t, i18n } = useTranslation();
  const query = useRecords(), rename = useRenameExercise(), remove = useDeleteExercise();
  const [editing, setEditing] = useState<Exercise | null>(null), [name, setName] = useState("");
  const [search, setSearch] = useState("");
  const [workout, setWorkout] = useState<Workout | null>(null);
  const open = useMutation({ mutationFn: (id: number) => api<Workout>(`/workouts/${id}`), onSuccess: setWorkout });
  if (query.isPending) return <Skeleton />;
  if (query.isError) return <QueryError error={query.error} retry={() => void query.refetch()} />;
  return <section className="rounded-3xl bg-surface p-5">
    <h2 className="font-medium">{t("records.title")}</h2><p className="mt-2 text-sm text-muted">{t("records.hint")}</p>
    {!query.data.length && <p className="mt-3 text-sm text-muted">{t("records.empty")}</p>}
    {!!query.data.length && <input type="search" aria-label={t("records.search")} placeholder={t("records.search")} value={search} onChange={e => setSearch(e.target.value)} className="mt-4 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text" />}
    {query.data.filter(row => row.exercise.name.toLocaleLowerCase().includes(search.toLocaleLowerCase())).map(data => <ExerciseProgressCard key={data.exercise.id} data={data} onOpen={id => open.mutate(id)}>
      <div className="mt-3 flex gap-5 text-sm"><button type="button" className="min-h-11 text-primary" onClick={() => { setEditing(data.exercise); setName(data.exercise.name); rename.reset(); }}>{t("records.rename")}</button>
        <button type="button" disabled={remove.isPending} className="min-h-11 text-danger" onClick={async () => {
          if (await confirmAction(t("records.deleteExerciseConfirm", { name: data.exercise.name }))) remove.mutate(data.exercise.id);
        }}>{t("workout.delete")}</button></div>
    </ExerciseProgressCard>)}
    <WriteError error={open.error} />
    {workout && <ExerciseLogsSheet workout={workout} onClose={() => setWorkout(null)} />}
    <WriteError error={remove.error} />
    {editing && <Modal title={t("records.rename")} onClose={() => { if (!rename.isPending) setEditing(null); }}>
      <form onSubmit={event => { event.preventDefault(); rename.mutate({ id: editing.id, name }, { onSuccess: () => setEditing(null) }); }}>
        <h2 className="font-semibold">{t("records.rename")}</h2>
        <label className="mt-3 block text-sm text-muted">{t("records.name")}<input required maxLength={80} value={name} disabled={rename.isPending} onChange={event => setName(event.target.value)} className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text" /></label>
        <WriteError error={rename.error} /><PrimaryButton type="submit" disabled={rename.isPending || !name.trim()}>{t("records.saveName")}</PrimaryButton>
        <button type="button" disabled={rename.isPending} onClick={() => setEditing(null)} className="mt-3 min-h-11 text-muted">{t("common.cancel")}</button>
      </form>
    </Modal>}
  </section>;
}
