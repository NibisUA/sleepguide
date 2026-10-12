import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { Modal } from "../../components/Modal";
import { api } from "../../lib/api";
import type { DataExport } from "../../types/api";

export function PrivacySection({ onDeleted }: { onDeleted: () => void }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const exportData = useMutation({
    mutationKey: ["account", "export"],
    mutationFn: async () => {
      const data = await api<DataExport>("/me/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url; link.download = `sleepguide-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.append(link); link.click(); link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    },
  });
  const remove = useMutation({
    mutationKey: ["account", "delete"],
    mutationFn: async () => {
      await qc.cancelQueries();
      await api<void>("/me", { method: "DELETE", body: JSON.stringify({ confirm: true }) });
    },
    onSuccess: () => { qc.clear(); onDeleted(); },
  });
  function close() { if (!remove.isPending) { setOpen(false); setConfirmed(false); remove.reset(); } }
  return <section className="rounded-3xl bg-surface p-5">
    <h2 className="font-medium">{t("privacy.settingsTitle")}</h2>
    <a href={`/privacy/${i18n.language.startsWith("uk") ? "uk" : "en"}`} className="mt-3 block py-2 text-primary">{t("privacy.title")}</a>
    <p className="mt-2 text-sm text-muted">{t("privacy.exportHint")}</p>
    <button type="button" disabled={exportData.isPending} onClick={() => exportData.mutate()}
      className="mt-3 w-full rounded-2xl border border-primary/50 py-3 text-primary disabled:opacity-60">
      {exportData.isPending ? t("common.loading") : t("privacy.export")}
    </button>
    {exportData.isSuccess && <p role="status" className="mt-2 text-sm text-primary">{t("privacy.exportReady")}</p>}
    {exportData.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}</p>}
    <button type="button" onClick={() => setOpen(true)} className="mt-4 min-h-11 text-sm text-danger">{t("privacy.delete")}</button>
    {open && <Modal title={t("privacy.deleteTitle")} onClose={close}>
      <h2 className="text-lg font-semibold">{t("privacy.deleteTitle")}</h2>
      <p className="mt-3 text-sm text-muted">{t("privacy.deleteWarning")}</p>
      <label className="mt-4 flex items-start gap-3 text-sm">
        <input type="checkbox" checked={confirmed} disabled={remove.isPending}
          onChange={event => setConfirmed(event.target.checked)} className="mt-1 h-5 w-5 shrink-0 accent-danger" />
        {t("privacy.confirm")}
      </label>
      {remove.isError && <p role="alert" className="mt-3 text-sm text-danger">{t("common.error")}</p>}
      <button type="button" disabled={!confirmed || remove.isPending} onClick={() => remove.mutate()}
        className="mt-5 w-full rounded-2xl bg-danger-button py-3 font-semibold text-white disabled:opacity-50">
        {remove.isPending ? t("common.loading") : t("privacy.deleteForever")}
      </button>
      <button type="button" disabled={remove.isPending} onClick={close}
        className="mt-3 w-full rounded-2xl border border-muted/30 py-3 text-muted">{t("common.cancel")}</button>
    </Modal>}
  </section>;
}
