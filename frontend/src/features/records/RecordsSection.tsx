import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { QueryError, Skeleton } from "../../components/QueryState";
import { PrimaryButton } from "../../components/ui";
import { confirmAction } from "../../lib/confirm";
import { formatDate } from "../../lib/format";
import type { Exercise } from "../../types/api";
import { useDeleteExercise, useRecords, useRenameExercise } from "./api";
import { WriteError } from "./ExerciseLogsSheet";
import { logText, recordText } from "./format";

export function RecordsSection() {
  const { t, i18n } = useTranslation();
  const query = useRecords(), rename = useRenameExercise(), remove = useDeleteExercise();
  const [editing, setEditing] = useState<Exercise | null>(null), [name, setName] = useState("");
  if (query.isPending) return <Skeleton />;
  if (query.isError) return <QueryError error={query.error} retry={() => void query.refetch()} />;
  return <section className="rounded-3xl bg-surface p-5">
    <h2 className="font-medium">{t("records.title")}</h2><p className="mt-2 text-sm text-muted">{t("records.hint")}</p>
    {!query.data.length && <p className="mt-3 text-sm text-muted">{t("records.empty")}</p>}
    {query.data.map(({ exercise, records }) => <article key={exercise.id} className="mt-4 rounded-2xl bg-bg p-4">
      <h3 className="break-words font-semibold">{exercise.name}</h3>
      {!records.length && <p className="mt-2 text-sm text-muted">{t("records.noResults")}</p>}
      <dl className="mt-3 space-y-4">{records.map(record => <div key={`${record.metric}-${record.distance_m ?? ""}`}>
        <dt className="text-xs text-muted">{t(`records.metrics.${record.metric}`)}</dt>
        <dd className="mt-1 text-xl font-semibold text-primary">{recordText(record, t, i18n.language)}</dd>
        <dd className="mt-1 text-xs text-muted">{formatDate(record.date, i18n.language, { day: "numeric", month: "short", year: "numeric" })}
          {exercise.kind === "strength" ? ` · ${logText(record, t, i18n.language)}` : ""}</dd>
      </div>)}</dl>
      <div className="mt-3 flex gap-5 text-sm"><button type="button" className="min-h-11 text-primary" onClick={() => { setEditing(exercise); setName(exercise.name); rename.reset(); }}>{t("records.rename")}</button>
        <button type="button" disabled={remove.isPending} className="min-h-11 text-danger" onClick={async () => {
          if (await confirmAction(t("records.deleteExerciseConfirm", { name: exercise.name }))) remove.mutate(exercise.id);
        }}>{t("workout.delete")}</button></div>
    </article>)}
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
