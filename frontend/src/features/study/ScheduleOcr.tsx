import { useEffect, useRef, useState } from "react";
import type { Worker } from "tesseract.js";

export function ScheduleOcr({ onText }: { onText: (text: string) => void }) {
  const [progress, setProgress] = useState<string | null>(null), [error, setError] = useState("");
  const worker = useRef<Worker | null>(null), alive = useRef(true), running = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; void worker.current?.terminate(); }; }, []);
  async function recognize(files: File[]) {
    if (running.current || !files.length) return;
    if (files.length > 8 || files.some(file => !["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 10*1024*1024)) { setError("Вибери до 8 PNG, JPEG або WebP, кожен до 10 МБ."); return; }
    running.current = true; setError(""); setProgress("Завантаження локального OCR…");
    try {
      const { createWorker, PSM } = await import("tesseract.js");
      if (!alive.current) return;
      const w = await createWorker("eng+ukr", 1, { workerPath: "/ocr/worker.min.js", corePath: "/ocr/core", langPath: "/ocr/lang", cacheMethod: "none" });
      if (!alive.current) { await w.terminate(); return; } worker.current = w;
      await w.setParameters({ tessedit_pageseg_mode: PSM.AUTO });
      const results: string[] = [];
      for (const [index, file] of files.entries()) {
        if (!alive.current) return;
        setProgress(`Розпізнавання ${index+1} із ${files.length}…`);
        const url = URL.createObjectURL(file);
        try {
          const image = new Image(); image.src = url; await image.decode();
          if (image.naturalWidth*image.naturalHeight > 20_000_000 || Math.max(image.naturalWidth, image.naturalHeight) > 8000) throw new Error("Зображення завелике: до 20 мегапікселів і 8000 px на сторону.");
          const canvas = document.createElement("canvas"), scale = Math.min(1, 3000/Math.max(image.naturalWidth, image.naturalHeight));
          canvas.width = Math.max(1, Math.round(image.naturalWidth*scale)); canvas.height = Math.max(1, Math.round(image.naturalHeight*scale));
          const ctx = canvas.getContext("2d"); if (!ctx) throw new Error("Браузер не підтримує обробку зображень");
          ctx.fillStyle = "white"; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
          const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height); let brightness = 0;
          for (let n = 0; n < pixels.data.length; n += 16) brightness += (pixels.data[n]+pixels.data[n+1]+pixels.data[n+2])/3;
          if (brightness/(pixels.data.length/16) < 110) { for (let n = 0; n < pixels.data.length; n += 4) for (let c = 0; c < 3; c++) pixels.data[n+c] = 255-pixels.data[n+c]; ctx.putImageData(pixels, 0, 0); }
          const result = await w.recognize(canvas);
          if (!result.data.text.trim()) throw new Error(`На скриншоті ${index+1} не знайдено тексту. Спробуй чіткіше зображення.`);
          results.push(result.data.text);
        } finally { URL.revokeObjectURL(url); }
      }
      if (alive.current) onText(results.join("\n\n"));
    } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : "OCR не вдалося виконати. Спробуй інше фото або встав текст."); }
    finally { const w = worker.current; worker.current = null; await w?.terminate(); running.current = false; if (alive.current) setProgress(null); }
  }
  return <div className="mt-3 space-y-2">
    <p className="text-sm text-muted">Фото розпізнаються на пристрої. Порядок скриншотів зберігається; перевір текст після OCR.</p>
    <label className="block text-sm">Скриншоти розкладу<input type="file" multiple accept="image/png,image/jpeg,image/webp" disabled={!!progress} className="mt-2 block w-full text-sm" onChange={e => { const files = Array.from(e.target.files ?? []); e.target.value = ""; void recognize(files); }} /></label>
    {progress && <p role="status" className="text-sm text-primary">{progress}</p>}
    {error && <p role="alert" className="text-sm text-danger">{error}</p>}
  </div>;
}
