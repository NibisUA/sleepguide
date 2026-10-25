import { lazy, Suspense, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Modal } from "../../components/Modal";
import { isoDate } from "../../lib/format";
import { WriteError } from "../records/WriteError";
import { itemsText, parseText, previewPlan, savePlan, textItems, useStudyMutation, shiftDay, type Item, type Parsed, type Plan, type PlanInput } from "./api";
const ScheduleOcr = lazy(() => import("./ScheduleOcr").then(m => ({ default: m.ScheduleOcr })));
const input = "mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text";

export function PlanForm({ plan, onClose }: { plan?: Plan; onClose: () => void }) {
  const [mode, setMode] = useState("manual"), [name, setName] = useState(plan?.name ?? "");
  const [deadline, setDeadline] = useState(plan?.deadline ?? ""), [start, setStart] = useState(plan?.start_date ?? isoDate(new Date()));
  const [total, setTotal] = useState(String(plan?.items.length ?? "")), [reserve, setReserve] = useState(String(plan?.reserve_days ?? 0));
  const [capacity, setCapacity] = useState(String(plan?.daily_capacity ?? "")), [source, setSource] = useState("");
  const [year, setYear] = useState(""), [parsed, setParsed] = useState<Parsed | null>(null), [reviewed, setReviewed] = useState(false);
  const [editor, setEditor] = useState(plan ? itemsText(plan.items) : ""), [preserve, setPreserve] = useState(!!plan);
  const [groups, setGroups] = useState<{ from: string; to: string; weight: string; name: string }[]>([]);
  const [stage, setStage] = useState<{ input: PlanInput; items: Item[]; days: number } | null>(null), [localError, setLocalError] = useState("");
  const parse = useMutation({ mutationFn: () => parseText(source, year ? Number(year) : null), onSuccess: result => {
    setParsed(result); setReviewed(false); setEditor(itemsText(result.items)); setTotal(String(result.declared_total ?? result.total));
    if (result.name) setName(result.name); if (result.deadline) setDeadline(result.deadline); if (result.start_date) setStart(result.start_date);
    setReserve(String(result.reserve_days)); setPreserve(result.preserve_schedule); setStage(null);
  } });
  const preview = useMutation({ mutationFn: (body: PlanInput) => previewPlan(body, plan?.id), onSuccess: (result, body) => setStage({ input: body, items: result.items, days: result.working_days }) });
  const save = useStudyMutation((body: PlanInput) => savePlan(body, plan?.id));
  const busy = parse.isPending || preview.isPending || save.isPending;
  function changeTotal(value: string) {
    setTotal(value);
    const n = Number(value);
    if (!editor.trim() || !Number.isInteger(n) || n < 1 || n > 1000) return;
    try {
      const old = textItems(editor);
      if (old.every((row, index) => row.label === String(index+1))) {
        setEditor(itemsText(Array.from({ length: n }, (_, index) => old[index] ?? { label: String(index+1), title: "", group: "", weight: 1, scheduled_date: null })));
        setPreserve(false);
      }
    } catch { /* Keep custom rows intact until the user fixes them. */ }
  }
  function prepare() {
    setLocalError("");
    try {
      if (parsed?.reserve_dates.length) {
        const reserveDates = new Set(Array.from({ length: Number(reserve) }, (_, n) => shiftDay(deadline, -n-1)));
        if (parsed.reserve_dates.some(day => !reserveDates.has(day))) throw new Error("Дати запасу з джерела не збігаються з дедлайном і кількістю днів запасу. Виправ ці поля або джерело.");
      }
      const count = Number(total);
      let items: Item[] | undefined = editor.trim() ? textItems(editor) : undefined;
      if (mode !== "manual" && !parsed) throw new Error("Спочатку розпізнай текст або скриншоти.");
      if (parsed?.issues.length && !reviewed) throw new Error("Перевір позначені неоднозначності та підтвердь перевірку.");
      if (!items && groups.length) {
        items = Array.from({ length: count }, (_, n) => ({ label: String(n+1), title: "", group: "", weight: 1, scheduled_date: null }));
        const assigned = new Set<number>();
        for (const group of groups) {
          const a = Number(group.from), b = Number(group.to), w = Number(group.weight);
          if (![a,b,w].every(Number.isInteger) || a < 1 || b < a || b > count || w < 1 || w > 100) throw new Error("Перевір діапазони груп та складність 1–100.");
          for (let n = a; n <= b; n++) { if (assigned.has(n)) throw new Error("Діапазони груп перетинаються."); assigned.add(n); items[n-1] = { ...items[n-1], group: group.name, weight: w }; }
        }
      }
      if (items && new Set(items.map(row => row.label)).size !== items.length) throw new Error("Є повторні номери. Прибери дублікати.");
      if (items && items.length !== count) throw new Error(`Заявлено ${count}, фактично ${items.length}. Виправ кількість або список.`);
      if (!Number.isInteger(count) || count < 1 || count > 1000) throw new Error("Кількість питань: від 1 до 1000.");
      preview.mutate({ name, deadline, start_date: start, total: count, reserve_days: Number(reserve), daily_capacity: capacity ? Number(capacity) : null, items, preserve_schedule: preserve, expected_version: plan?.version });
    } catch (e) { setLocalError(e instanceof Error ? e.message : "Перевір дані"); }
  }
  const close = () => { if (!busy) onClose(); };
  return <Modal title={plan ? "Редагувати план" : "Новий план"} onClose={close}>
    <div className="flex items-center justify-between gap-2"><h2 className="text-lg font-semibold">{plan ? "Редагувати план" : "Новий план"}</h2><button type="button" disabled={busy} className="min-h-11 text-primary" onClick={close}>Закрити</button></div>
    {!stage ? <form className="mt-3 space-y-3" onSubmit={e => { e.preventDefault(); if (!busy) prepare(); }}>
      {!plan && <div className="flex flex-wrap gap-2" aria-label="Спосіб створення">{[["manual", "Вручну"], ["text", "Із тексту"], ["image", "Із фото"]].map(([value, label]) => <button type="button" key={value} aria-pressed={mode === value} className={`min-h-11 rounded-xl border px-3 text-sm ${mode === value ? "border-primary text-primary" : "border-muted/30 text-muted"}`} onClick={() => setMode(value)}>{label}</button>)}</div>}
      {mode !== "manual" && <div className="space-y-3">
        {mode === "image" && <Suspense fallback={<p role="status">Завантаження OCR…</p>}><ScheduleOcr onText={text => { setSource(text); setParsed(null); setReviewed(false); }} /></Suspense>}
        <label className="block text-sm">Текст для розпізнавання<textarea rows={6} maxLength={60000} className={input} value={source} onChange={e => { setSource(e.target.value); setParsed(null); setReviewed(false); }} placeholder="Встав власний перелік або розклад" /></label>
        <label className="block text-sm">Рік для дат без року (за потреби)<input type="number" min="2000" max="2100" className={input} value={year} onChange={e => { setYear(e.target.value); setParsed(null); setReviewed(false); }} /></label>
        <button type="button" disabled={busy || !source.trim()} className="min-h-11 rounded-xl border border-primary/50 px-4 text-primary" onClick={() => { setLocalError(""); parse.mutate(); }}>Розпізнати структуру</button>
        {parsed && <p role="status" className="text-sm text-muted">{parsed.preserve_schedule ? "Знайдено готовий розклад — дати збережено." : "Знайдено перелік — розподіл сформуємо за дедлайном."} Питань: {parsed.total}.</p>}
        {!!parsed?.issues.length && <div className="rounded-xl border border-warning/50 p-3 text-sm"><p className="font-medium">Потрібна перевірка</p><ul className="mt-2 list-inside list-disc">{parsed.issues.map((issue, n) => <li key={n}>{issue.line ? `Рядок ${issue.line}: ` : ""}{issue.message}</li>)}</ul><label className="mt-3 flex min-h-11 items-center gap-2"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />Я перевірив та виправив ці дані нижче</label></div>}
        <WriteError error={parse.error} />
      </div>}
      <label className="block text-sm">Назва предмета або цілі<input required maxLength={120} className={input} value={name} onChange={e => setName(e.target.value)} /></label>
      <div className="grid grid-cols-2 gap-3"><label className="block text-sm">Дедлайн<input required type="date" className={`${input} min-w-0`} value={deadline} onChange={e => setDeadline(e.target.value)} /></label><label className="block text-sm">Кількість питань<input required type="number" min="1" max="1000" step="1" className={input} value={total} onChange={e => changeTotal(e.target.value)} /></label></div>
      <details open={mode !== "manual" || !!plan}><summary className="min-h-11 py-3 text-sm text-primary">Дати, запас і складність — необов’язково</summary>
        <div className="space-y-3"><label className="block text-sm">Дата початку<input type="date" required className={input} value={start} onChange={e => setStart(e.target.value)} /></label>
          <label className="block text-sm">Днів запасу перед дедлайном<input type="number" required min="0" max="365" className={input} value={reserve} onChange={e => setReserve(e.target.value)} /></label>
          <p className="text-xs text-muted">Дедлайн — день здачі. Нові питання розподіляються до нього, без днів запасу.</p>
          <label className="block text-sm">Денний ліміт складності (необов’язково)<input type="number" min="1" max="10000" className={input} value={capacity} onChange={e => setCapacity(e.target.value)} /></label>
          {!editor && <><p className="text-sm">Групи: звичайне питання має вагу 1</p>{groups.map((group, i) => <div key={i} className="space-y-2 border-t border-muted/20 pt-3">
            <div className="grid grid-cols-3 gap-2">{([['from', 'Від №'], ['to', 'До №'], ['weight', 'Вага']] as const).map(([key, label]) => <label key={key} className="text-xs">{label}<input aria-label={`${label} групи ${i+1}`} className={input} type="number" min="1" required value={group[key]} onChange={e => setGroups(groups.map((row, j) => i === j ? { ...row, [key]: e.target.value } : row))} /></label>)}</div>
            <label className="block text-xs">Назва групи<input className={input} maxLength={80} value={group.name} onChange={e => setGroups(groups.map((row, j) => i === j ? { ...row, name: e.target.value } : row))} /></label>
            <button type="button" className="min-h-11 text-sm text-danger" onClick={() => setGroups(groups.filter((_, j) => j !== i))}>Прибрати групу</button></div>)}
            <button type="button" className="min-h-11 text-sm text-primary" onClick={() => setGroups([...groups, { from: "1", to: total, weight: "1", name: "" }])}>+ Група складності</button></>}
          <label className="block text-sm">Власні номери та дати<textarea rows={6} className={`${input} font-mono text-sm`} value={editor} onChange={e => { setEditor(e.target.value); setReviewed(false); }} /><span className="mt-1 block text-xs text-muted">Кожен рядок: номер | дата YYYY-MM-DD або порожньо | вага | група | коротка назва. Для простого плану залиш порожнім.</span></label>
          {!!editor.trim() && <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={preserve} onChange={e => setPreserve(e.target.checked)} />Зберегти вказані дати; інакше розподілити невиконане заново</label>}
        </div>
      </details>
      {localError && <p role="alert" className="text-sm text-danger">{localError}</p>}<WriteError error={preview.error} />
      <button type="submit" disabled={busy} className="min-h-11 w-full rounded-2xl bg-primary px-4 py-3 font-medium text-on-primary">{busy ? "Обробка…" : "Переглянути план"}</button>
    </form> : <div className="mt-3 space-y-3">
      <p className="font-medium">{stage.input.name} · {stage.items.length} питань</p><p className="text-sm text-muted">Робочих днів від сьогодні: {stage.days}. Запас: {stage.input.reserve_days} дн.</p>
      {stage.items.some(row => !row.scheduled_date && !row.done_at) && <p role="alert" className="text-sm text-warning">Є питання без дати. Робочих днів може не вистачати; зміни дедлайн, запас або розподіл.</p>}
      <p className="text-xs text-muted">Дати можна виправити тут. Виконані питання залишаються без змін.</p>
      <div className="divide-y divide-muted/20">{stage.items.map((row, i) => <div key={row.label} className="grid grid-cols-[1fr_auto] items-center gap-2 py-2">
        <div className="min-w-0"><p className="break-words text-sm">{row.done_at ? "✓ " : ""}{row.label}{row.title ? ` · ${row.title}` : ""}</p><p className="text-xs text-muted">{row.group} · вага {row.weight}</p></div>
        <input aria-label={`Дата питання ${row.label}`} type="date" className="min-w-0 max-w-40 rounded-lg border border-muted/30 bg-bg p-2 text-sm" disabled={!!row.done_at || busy} value={row.scheduled_date ?? ""} onChange={e => setStage({ ...stage, items: stage.items.map((item, j) => i === j ? { ...item, scheduled_date: e.target.value || null } : item) })} />
      </div>)}</div>
      <WriteError error={save.error} />
      <button type="button" disabled={busy} className="min-h-11 w-full rounded-2xl bg-primary px-4 py-3 font-medium text-on-primary" onClick={() => save.mutate({ ...stage.input, items: stage.items, preserve_schedule: true }, { onSuccess: onClose })}>{busy ? "Збереження…" : "Зберегти план"}</button>
      <button type="button" disabled={busy} className="min-h-11 w-full text-primary" onClick={() => setStage(null)}>Повернутися до редагування</button>
    </div>}
  </Modal>;
}
