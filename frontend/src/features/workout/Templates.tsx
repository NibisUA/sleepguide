import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { confirmAction } from "../../lib/confirm";
import { QueryError } from "../../components/QueryState";
import { WriteError } from "../records/WriteError";
import type { Workout } from "../../types/api";
import type { components } from "../../types/api.gen";
type Template = components["schemas"]["TemplateOut"];

export function useRepeatWorkout() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => api<Workout>(`/workouts/${id}/repeat`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries() });
}

export function SaveTemplate({ workout }: { workout: Workout }) {
  const { t } = useTranslation(), qc = useQueryClient();
  const [open, setOpen] = useState(false), [name, setName] = useState("");
  const save = useMutation({ mutationFn: () => api<Template>("/workout-templates", { method: "POST", body: JSON.stringify({ name, workout_id: workout.id }) }),
    onSuccess: () => { setOpen(false); setName(""); void qc.invalidateQueries({ queryKey: ["workout-templates"] }); } });
  return <div className="mt-3">
    {!open ? <button type="button" className="min-h-11 text-sm text-primary" onClick={() => { save.reset(); setOpen(true); }}>{t("templates.save")}</button> :
      <form onSubmit={event => { event.preventDefault(); if (!save.isPending) save.mutate(); }}>
        <label className="text-sm">{t("templates.name")}<input autoFocus required maxLength={80} value={name} disabled={save.isPending} onChange={e => setName(e.target.value)} className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3" /></label>
        <div className="flex gap-5"><button type="submit" disabled={!name.trim() || save.isPending} className="min-h-11 text-primary">{t("templates.save")}</button><button type="button" disabled={save.isPending} className="min-h-11 text-muted" onClick={() => setOpen(false)}>{t("common.cancel")}</button></div>
        <WriteError error={save.error} />
      </form>}
  </div>;
}

export function Templates() {
  const { t } = useTranslation(), qc = useQueryClient();
  const list = useQuery({ queryKey: ["workout-templates"], queryFn: () => api<Template[]>("/workout-templates") });
  const previous = useQuery({ queryKey: ["workouts", "latest-for-repeat"], queryFn: () => api<Workout[]>("/workouts?limit=2") });
  const repeat = useRepeatWorkout();
  const start = useMutation({ mutationFn: (id: number) => api<Workout>(`/workout-templates/${id}/start`, { method: "POST" }), onSuccess: () => qc.invalidateQueries() });
  const erase = useMutation({ mutationFn: (id: number) => api<void>(`/workout-templates/${id}`, { method: "DELETE" }), onSuccess: () => qc.invalidateQueries({ queryKey: ["workout-templates"] }) });
  const [expanded, setExpanded] = useState(false);
  const last = previous.data?.find(w => w.ended_at);
  const busy = repeat.isPending || start.isPending || erase.isPending;
  return <div className="mt-4 border-t border-muted/20 pt-3">
    {last && <button type="button" disabled={busy} className="min-h-11 w-full text-sm text-primary" onClick={() => repeat.mutate(last.id)}>{t("templates.repeatLast")}</button>}
    <h3 className="mt-2 font-medium">{t("templates.title")}</h3><p className="mt-1 text-xs text-muted">{t("templates.hint")}</p>
    {list.isError && <QueryError error={list.error} retry={() => void list.refetch()} />}
    {list.data?.length === 0 && <p className="mt-2 text-sm text-muted">{t("templates.empty")}</p>}
    <ul className="mt-2 divide-y divide-muted/10">{(expanded ? list.data : list.data?.slice(0, 3))?.map(row => <li key={row.id} className="py-2">
      <p className="break-words text-sm font-medium">{row.name}</p><p className="mt-1 text-xs text-muted">{t(`workout.types.${row.type}`)} · {t("templates.sets", { count: row.sets.length })}</p>
      <div className="flex gap-5"><button type="button" disabled={busy} className="min-h-11 text-sm text-primary" onClick={() => start.mutate(row.id)}>{t("templates.start")}</button><button type="button" disabled={busy} className="min-h-11 text-sm text-muted" onClick={async () => { if (await confirmAction(t("templates.eraseConfirm"))) erase.mutate(row.id); }}>{t("workout.delete")}</button></div>
    </li>)}</ul>
    {!expanded && (list.data?.length ?? 0) > 3 && <button type="button" className="min-h-11 text-primary" onClick={() => setExpanded(true)}>{t("templates.all")}</button>}
    <WriteError error={repeat.error ?? start.error ?? erase.error} />
  </div>;
}
