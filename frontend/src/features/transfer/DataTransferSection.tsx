import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import type { components } from "../../types/api.gen";
import { SCREEN_CATEGORIES } from "../screentime/categories";
import { formatDuration } from "../../lib/format";

type S = components["schemas"];
type Kind = S["CsvImportIn"]["kind"];
type Preview = S["CsvPreviewOut"];
const templates: Record<NonNullable<Kind>, string> = {
  sleep: "Дата,Час коли заснув,Час коли прокинувся\n26.09.2026,23:30,07:30\n27.09.2026,01:15,09:00\n",
  workout: "Дата,Початок,Кінець,type,intensity\n26.09.2026,18:00,19:00,gym,moderate\n",
  stress: "Дата,Час,level,category\n26.09.2026,18:00,3,work\n",
  screen: "Дата,total_minutes,before_bed_minutes,social_minutes,entertainment_minutes,games_minutes\n26.09.2026,542,30,326,73,53\n",
};

function download(csv: string, filename: string) {
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url; link.download = filename;
  document.body.append(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function DataTransferSection({ onImported }: { onImported?: () => void } = {}) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const [kind, setKind] = useState<NonNullable<Kind>>("sleep");
  const [text, setText] = useState("");
  const [filename, setFilename] = useState("");
  const [result, setResult] = useState<Preview | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const preview = useMutation({ mutationFn: () => api<Preview>("/data/preview", { method: "POST", body: JSON.stringify({ kind, csv: text }) }), onSuccess: setResult });
  const save = useMutation({ mutationFn: () => api<Preview>("/data/import", { method: "POST", body: JSON.stringify({ kind, csv: text }) }),
    onSuccess: async data => { setResult(data); await qc.invalidateQueries(); onImported?.(); } });
  const exportData = useMutation({ mutationFn: async () => {
    const data = await api<S["CsvExportOut"]>(`/data/export/${kind}`);
    download(data.csv, data.filename);
  } });
  const busy = reading || preview.isPending || save.isPending || exportData.isPending;
  const error = preview.error ?? save.error ?? exportData.error;
  const errorKey = error instanceof ApiError && i18n.exists(`errors.${error.code}`) ? `errors.${error.code}` : "common.error";
  function reset() { setResult(null); setFileError(null); preview.reset(); save.reset(); exportData.reset(); }
  async function readFile(file: File) {
    reset(); setText(""); setFilename(file.name); setReading(true);
    try {
      if (file.size > 1_000_000) throw new Error("size");
      const value = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
      setText(value);
    } catch { setFileError(t("transfer.fileError")); }
    finally { setReading(false); }
  }
  return <section className="rounded-3xl bg-surface p-5">
    <h2 className="font-medium">{t("transfer.title")}</h2>
    <p className="mt-2 text-sm text-muted">{t("transfer.hint")}</p>
    <label className="mt-4 block text-sm text-muted">{t("transfer.kind")}
      <select disabled={busy} value={kind} onChange={e => { setKind(e.target.value as NonNullable<Kind>); setText(""); setFilename(""); reset(); }} className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text">
        {Object.keys(templates).map(value => <option key={value} value={value}>{t(`quick.${value}`)}</option>)}
      </select>
    </label>
    <p className="mt-3 text-xs text-muted">{t(kind === "sleep" ? "transfer.dateHint" : "transfer.otherHint")}</p>
    <div className="mt-3 flex flex-wrap gap-3 text-sm">
      <button type="button" disabled={busy} onClick={() => download("\ufeff" + templates[kind], `sleepguide-${kind}-template.csv`)} className="min-h-11 text-primary">{t("transfer.template")}</button>
      <button type="button" disabled={busy} onClick={() => exportData.mutate()} className="min-h-11 text-primary">{t("transfer.export")}</button>
    </div>
    {exportData.isSuccess && <p role="status" className="mt-2 text-sm text-primary">{t("transfer.exported")}</p>}
    <label className="mt-3 block text-sm text-muted">{t("transfer.file")}
      <input key={kind} type="file" accept=".csv,text/csv,text/plain" disabled={busy} onChange={e => { const file = e.target.files?.[0]; if (file) void readFile(file); e.target.value = ""; }} className="mt-2 block w-full text-sm" />
    </label>
    {filename && <p className="mt-2 break-all text-xs text-muted">{filename}</p>}
    <button type="button" onClick={() => setShowPaste(!showPaste)} className="mt-2 min-h-11 text-sm text-primary">{t("transfer.paste")}</button>
    {showPaste && <label className="mt-2 block text-sm text-muted">CSV<textarea rows={5} maxLength={1_000_000} disabled={busy} value={text} onChange={e => { setText(e.target.value); setFilename(""); reset(); }} className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 font-mono text-xs text-text" /></label>}
    <button type="button" disabled={busy || !text.trim()} onClick={() => { reset(); preview.mutate(); }} className="mt-3 w-full rounded-xl border border-primary/50 py-3 text-primary disabled:opacity-50">{preview.isPending ? t("common.loading") : t("transfer.preview")}</button>
    {(fileError || error) && <p role="alert" className="mt-3 text-sm text-danger">{fileError ?? t(errorKey)}</p>}
    {result && <div className="mt-4">
      <p className="text-sm">{t("transfer.counts", { ready: result.ready, duplicates: result.duplicates, errors: result.errors })}</p>
      <p className="mt-1 text-xs text-muted">{result.timezone} · {t("transfer.noOverwrite")}</p>
      <div className="mt-3 max-h-72 overflow-auto rounded-xl bg-bg">
        <table className="w-full text-left text-xs"><caption className="sr-only">{t("transfer.preview")}</caption>
          <thead><tr><th className="p-2">#</th><th className="p-2">{t("transfer.date")}</th><th className="p-2">{t("transfer.result")}</th></tr></thead>
          <tbody>{result.rows.map(row => <tr key={row.line} className="border-t border-muted/10">
            <td className="p-2">{row.line}</td><td className="p-2 whitespace-nowrap">{row.date}</td>
            <td className={`p-2 ${row.status === "error" ? "text-danger" : row.status === "duplicate" ? "text-muted" : "text-primary"}`}>{row.summary}
              {row.categories && <div className="mt-1 space-y-0.5 text-muted">{SCREEN_CATEGORIES.filter(({ field }) => field in row.categories!).map(({ field }) => <p key={field}>{t(`screen.categoryLabels.${field}`)}: {row.categories?.[field] == null ? "—" : formatDuration(t, row.categories[field])}</p>)}</div>}
              <span className="block">{row.code ? t(`errors.${row.code}`) : t("transfer.ready")}</span></td>
          </tr>)}</tbody></table>
      </div>
      {!save.isSuccess && <button type="button" disabled={busy || result.errors > 0 || result.ready === 0} onClick={() => save.mutate()} className="mt-3 w-full rounded-xl bg-primary py-3 font-semibold text-on-primary disabled:opacity-50">{save.isPending ? t("common.loading") : t("transfer.import", { count: result.ready })}</button>}
      {save.isSuccess && <p role="status" className="mt-3 text-sm text-primary">{t("transfer.imported", { count: result.imported })}</p>}
    </div>}
  </section>;
}
