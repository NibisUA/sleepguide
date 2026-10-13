import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { confirmAction } from "../../lib/confirm";
import { Modal } from "../../components/Modal";
import { QueryError, Skeleton } from "../../components/QueryState";
import { WriteError } from "../records/WriteError";
import type { components } from "../../types/api.gen";

type Entry = components["schemas"]["DeletedOut"];
function useTrash(enabled = true) {
  return useQuery({ queryKey: ["trash"], queryFn: () => api<Entry[]>("/trash"), enabled });
}
function useRestore() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => api<void>(`/trash/${id}/restore`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries() });
}

export function TrashSection() {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const list = useTrash(open), restore = useRestore(), qc = useQueryClient();
  const erase = useMutation({ mutationFn: (id: number) => api<void>(`/trash/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trash"] }) });
  const busy = restore.isPending || erase.isPending;
  return <>
    <button type="button" onClick={() => setOpen(true)} className="min-h-11 rounded-xl border border-muted/30 px-4 text-primary">{t("trash.title")}</button>
    {open && <Modal title={t("trash.title")} onClose={() => { if (!busy) setOpen(false); }}>
      <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">{t("trash.title")}</h2><button type="button" disabled={busy} onClick={() => setOpen(false)} className="min-h-11 text-primary">{t("day.close")}</button></div>
      <p className="mt-2 text-sm text-muted">{t("trash.hint")}</p>
      {list.isPending ? <Skeleton /> : list.isError ? <QueryError error={list.error} retry={() => void list.refetch()} /> : list.data.length ?
        <ul className="mt-3 divide-y divide-muted/20">{list.data.map(row => <li key={row.id} className="py-3">
          <p className="text-sm font-medium">{t(`trash.kinds.${row.kind}`)} · {row.label}</p>
          <p className="mt-1 text-xs text-muted">{t("trash.until", { date: new Date(row.expires_at).toLocaleDateString(i18n.language) })}</p>
          <div className="mt-1 flex gap-5"><button type="button" disabled={busy} className="min-h-11 text-primary" onClick={() => restore.mutate(row.id)}>{t("trash.restore")}</button>
            <button type="button" disabled={busy} className="min-h-11 text-danger" onClick={async () => { if (await confirmAction(t("trash.eraseConfirm"))) erase.mutate(row.id); }}>{t("trash.erase")}</button></div>
        </li>)}</ul> : <p className="mt-4 text-muted">{t("trash.empty")}</p>}
      <WriteError error={restore.error ?? erase.error} />
    </Modal>}
  </>;
}

export function UndoNotice() {
  const { t } = useTranslation();
  const [target, setTarget] = useState<{ kind: string; recordId: string } | null>(null);
  const list = useTrash(!!target), restore = useRestore(), qc = useQueryClient();
  useEffect(() => {
    function onDelete(event: Event) {
      restore.reset(); setTarget((event as CustomEvent).detail);
      void qc.invalidateQueries({ queryKey: ["trash"] });
    }
    window.addEventListener("diary-deleted", onDelete);
    return () => window.removeEventListener("diary-deleted", onDelete);
  }, [qc, restore.reset]);
  const entry = list.data?.find(row => row.kind === target?.kind && row.record_key === target?.recordId);
  if (!target) return null;
  return <div role="status" className="fixed inset-x-4 bottom-24 z-30 mx-auto max-w-md rounded-2xl border border-muted/30 bg-surface p-4 shadow-xl">
    <div className="flex items-center gap-3"><span className="flex-1 text-sm">{t("trash.deleted")}</span>
      <button type="button" disabled={!entry || restore.isPending} className="min-h-11 text-primary disabled:opacity-50" onClick={() => entry && restore.mutate(entry.id, { onSuccess: () => setTarget(null) })}>{t("trash.undo")}</button>
      <button type="button" disabled={restore.isPending} aria-label={t("day.close")} className="min-h-11 px-2 text-muted" onClick={() => setTarget(null)}>×</button></div>
    <WriteError error={restore.error ?? list.error} />
  </div>;
}
