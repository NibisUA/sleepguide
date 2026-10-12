import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { formatDuration } from "../../lib/format";
import type { Baselines } from "../../types/api";

type Kind = Baselines["metrics"][number]["key"];
export function ShareCard({ data }: { data: Baselines }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  return <><button type="button" className="mt-4 w-full rounded-2xl border border-primary/40 py-3 text-sm text-primary"
    onClick={() => setOpen(true)}>{t("personal.share.open")}</button>
    {open && <SharePreview data={data} language={i18n.language} onClose={() => setOpen(false)} />}</>;
}

function SharePreview({ data, language, onClose }: { data: Baselines; language: string; onClose: () => void }) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<Kind[]>(["sleep", "workout"]);
  const [period, setPeriod] = useState<"recent" | "baseline">("recent");
  const [preview, setPreview] = useState<{ url: string; file: File } | null>(null);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const from = period === "recent" ? data.recent_from : data.baseline_from;
  const to = period === "recent" ? data.recent_to : data.baseline_to;
  useEffect(() => {
    let disposed = false;
    let url: string | undefined;
    setPreview(null); setError(false);
    const canvas = document.createElement("canvas");
    canvas.width = 1080; canvas.height = 1080;
    const ctx = canvas.getContext("2d");
    if (!ctx) { setError(true); return; }
    ctx.fillStyle = "#102321"; ctx.fillRect(0, 0, 1080, 1080);
    ctx.fillStyle = "#5ce0b7"; ctx.font = "bold 58px sans-serif"; ctx.fillText("SleepGuide", 70, 110);
    ctx.fillStyle = "#ecf6f2"; ctx.font = "32px sans-serif";
    ctx.fillText(`${from} — ${to}`, 70, 170);
    ctx.fillStyle = "#9cbbb2"; ctx.font = "27px sans-serif";
    ctx.fillText(t("personal.share.subtitle"), 70, 215);
    const metrics = data.metrics.filter(m => selected.includes(m.key));
    metrics.forEach((m, index) => {
      const y = 280 + index * 155;
      const value = period === "recent" ? m.recent : m.baseline;
      const days = period === "recent" ? m.recent_days : m.baseline_days;
      const text = value === null ? "—" : m.key === "sleep" || m.key === "screen" ? formatDuration(t, Math.round(value)) :
        `${value.toLocaleString(language, { maximumFractionDigits: 1 })}${m.key === "stress" ? "/5" : ` ${t("personal.goals.daysUnit")}`}`;
      ctx.fillStyle = "#193631"; ctx.fillRect(50, y, 980, 130);
      ctx.fillStyle = "#9cbbb2"; ctx.font = "28px sans-serif";
      ctx.fillText(t(`personal.baselines.${m.key}`), 80, y + 38);
      ctx.fillStyle = "#ecf6f2"; ctx.font = "bold 43px sans-serif"; ctx.fillText(text, 80, y + 94);
      ctx.textAlign = "right"; ctx.font = "24px sans-serif"; ctx.fillStyle = "#9cbbb2";
      ctx.fillText(t("personal.share.sample", { n: days }), 990, y + 94); ctx.textAlign = "left";
    });
    ctx.fillStyle = "#9cbbb2"; ctx.font = "25px sans-serif";
    ctx.fillText(t("personal.share.footer"), 70, 1005);
    canvas.toBlob(blob => {
      if (disposed) return;
      if (!blob) { setError(true); return; }
      url = URL.createObjectURL(blob);
      setPreview({ url, file: new File([blob], `sleepguide-${from}-${to}.png`, { type: "image/png" }) });
    }, "image/png");
    return () => { disposed = true; if (url) URL.revokeObjectURL(url); };
  }, [data, selected, period, language, from, to, t]);
  async function share() {
    if (!preview) return;
    setBusy(true); setError(false);
    try { await navigator.share({ files: [preview.file], title: "SleepGuide" }); }
    catch (e) { if (!(e instanceof DOMException && e.name === "AbortError")) setError(true); }
    finally { setBusy(false); }
  }
  return <Modal title={t("personal.share.open")} onClose={onClose}>
    <h2 className="text-lg font-semibold">{t("personal.share.open")}</h2>
    <p className="mt-2 text-sm text-muted">{t("personal.share.privacy")}</p>
    <div className="mt-4 flex gap-2">{(["recent", "baseline"] as const).map(p => <button key={p} type="button" aria-pressed={period === p}
      disabled={busy} onClick={() => setPeriod(p)} className={`flex-1 rounded-xl border px-2 py-3 text-sm ${p === period ? "border-primary text-primary" : "border-muted/30"}`}>{t(`personal.baselines.${p}`)}</button>)}</div>
    <div className="mt-4 grid grid-cols-2 gap-3">{data.metrics.map(m => <label key={m.key} className="flex items-center gap-2 text-sm">
      <input type="checkbox" className="accent-primary" checked={selected.includes(m.key)} disabled={busy || (selected.length === 1 && selected.includes(m.key))}
        onChange={e => setSelected(old => e.target.checked ? [...old, m.key] : old.filter(k => k !== m.key))} />{t(`personal.baselines.${m.key}`)}</label>)}</div>
    {preview && <img src={preview.url} alt={t("personal.share.preview")} className="mt-4 w-full rounded-2xl" />}
    {error && <p role="alert" className="mt-3 text-danger">{t("common.error")}</p>}
    <div className="mt-4 flex flex-wrap gap-3">
      {preview && <a download={preview.file.name} href={preview.url} className="flex-1 rounded-2xl bg-primary px-4 py-3 text-center font-semibold text-on-primary">{t("personal.share.download")}</a>}
      {preview && navigator.canShare?.({ files: [preview.file] }) && <button type="button" disabled={busy} onClick={() => void share()}
        className="flex-1 rounded-2xl border border-primary/40 px-4 py-3 text-primary">{t("personal.share.send")}</button>}
      <button type="button" onClick={onClose} className="w-full py-3 text-muted">{t("common.close")}</button>
    </div>
  </Modal>;
}
