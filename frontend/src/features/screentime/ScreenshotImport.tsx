import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { Worker } from "tesseract.js";
import { Modal } from "../../components/Modal";
import { formatDuration } from "../../lib/format";
import { categoryCandidates, durationCandidates, type DurationCandidate } from "./ocrParser";
import { SCREEN_CATEGORIES, type ScreenCategories } from "./categories";

export function ScreenshotImport({ onPick, onClose }: { onPick: (minutes: number, categories?: ScreenCategories) => void; onClose: () => void }) {
  const { t } = useTranslation();
  const [candidates, setCandidates] = useState<DurationCandidate[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [language, setLanguage] = useState("eng+ukr");
  const [categories, setCategories] = useState<ScreenCategories>({});
  const [includeCategories, setIncludeCategories] = useState(true);
  const active = useRef(true);
  const worker = useRef<Worker | null>(null);
  const objectUrl = useRef<string | null>(null);
  useEffect(() => { active.current = true; return () => {
    active.current = false; void worker.current?.terminate(); worker.current = null;
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
  }; }, []);
  async function read(file: File | undefined) {
    if (!file || progress !== null) return;
    setError(null); setCandidates([]);
    setCategories({}); setIncludeCategories(true);
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 10 * 1024 * 1024) {
      setError(t("ocr.invalid")); return;
    }
    setProgress(0);
    try {
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
      const url = URL.createObjectURL(file); objectUrl.current = url; setPreview(url);
      const image = new Image(); image.src = url; await image.decode();
      if (!active.current) return;
      if (image.naturalWidth * image.naturalHeight > 20_000_000 || Math.max(image.naturalWidth, image.naturalHeight) > 8000) throw new Error("large_image");
      const canvas = document.createElement("canvas");
      const scale = Math.min(1, 2400 / Math.max(image.naturalWidth, image.naturalHeight));
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale)); canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const ctx = canvas.getContext("2d"); if (!ctx) throw new Error("canvas");
      ctx.fillStyle = "white"; ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      // Normalize dark-mode screenshots locally before recognition.
      const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
      let brightness = 0;
      for (let i = 0; i < pixels.data.length; i += 16) brightness += (pixels.data[i] + pixels.data[i + 1] + pixels.data[i + 2]) / 3;
      if (brightness / (pixels.data.length / 16) < 110) {
        for (let i = 0; i < pixels.data.length; i += 4) for (let c = 0; c < 3; c++) pixels.data[i + c] = 255 - pixels.data[i + c];
        ctx.putImageData(pixels, 0, 0);
      }
      const { createWorker, PSM } = await import("tesseract.js");
      if (!active.current) return;
      const w = await createWorker(language, 1, {
        workerPath: "/ocr/worker.min.js", corePath: "/ocr/core", langPath: "/ocr/lang", cacheMethod: "none",
        logger: info => { if (active.current && info.status === "recognizing text") setProgress(Math.round(info.progress * 100)); },
      });
      if (!active.current) { await w.terminate(); return; }
      worker.current = w;
      await w.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT });
      const result = await w.recognize(canvas, {}, { blocks: true });
      if (!active.current) return;
      const found = durationCandidates(result.data.text);
      setCandidates(found);
      setCategories(categoryCandidates(result.data.text, result.data.blocks?.flatMap(block => block.paragraphs.flatMap(paragraph => paragraph.lines.flatMap(line => line.words))) ?? []));
      if (!found.length) setError(t("ocr.noMatch"));
    } catch (e) {
      if (active.current) setError(t(e instanceof Error && e.message === "large_image" ? "ocr.invalid" : "ocr.failed"));
    } finally {
      const w = worker.current; worker.current = null; await w?.terminate();
      if (active.current) setProgress(null);
    }
  }
  return <Modal title={t("ocr.title")} onClose={onClose}>
    <h2 className="text-lg font-semibold">{t("ocr.title")}</h2>
    <p className="mt-2 text-sm text-muted">{t("ocr.privacy")}</p>
    <label className="mt-4 block text-sm">{t("ocr.language")}
      <select value={language} disabled={progress !== null} onChange={e => setLanguage(e.target.value)} className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3">
        <option value="eng+ukr">Українська + English</option><option value="eng">English</option>
      </select></label>
    <label className="mt-4 block text-sm">{t("ocr.file")}
      <input type="file" accept="image/png,image/jpeg,image/webp" disabled={progress !== null}
        onChange={e => { const file = e.target.files?.[0]; e.target.value = ""; void read(file); }} className="mt-2 block w-full text-sm" /></label>
    {preview && <img src={preview} alt={t("ocr.preview")} className="mt-4 max-h-60 w-full rounded-xl object-contain" />}
    {progress !== null && <p role="status" className="mt-3 text-sm text-primary">{t("ocr.progress", { n: progress })}</p>}
    {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    {Object.keys(categories).length > 0 && <div className="mt-4 rounded-xl bg-surface p-3">
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={includeCategories} onChange={e => setIncludeCategories(e.target.checked)} className="accent-primary" />{t("ocr.includeCategories")}</label>
      <dl className="mt-2 space-y-1 text-sm">{SCREEN_CATEGORIES.filter(({ field }) => categories[field] != null).map(({ field, textColor }) => <div key={field} className="flex justify-between gap-3"><dt className={textColor}>{t(`screen.categoryLabels.${field}`)}</dt><dd>{formatDuration(t, categories[field]!)}</dd></div>)}</dl>
      <p className="mt-2 text-xs text-muted">{t("ocr.categoriesReview")}</p>
    </div>}
    {candidates.length > 0 && <><p className="mt-4 text-sm">{t("ocr.choose")}</p><div className="mt-3 space-y-2">{candidates.map(c => <button key={c.minutes} type="button"
      disabled={includeCategories && Object.values(categories).reduce<number>((n, value) => n + (value ?? 0), 0) > c.minutes}
      onClick={() => onPick(c.minutes, includeCategories && Object.keys(categories).length ? categories : undefined)} className="w-full rounded-xl border border-primary/40 p-3 text-left disabled:opacity-40">
      <span className="font-semibold text-primary">{formatDuration(t, c.minutes)}</span><span className="mt-1 block truncate text-xs text-muted">{c.text}</span>
    </button>)}</div></>}
    <button type="button" onClick={onClose} className="mt-4 w-full py-3 text-muted">{t("common.close")}</button>
  </Modal>;
}
