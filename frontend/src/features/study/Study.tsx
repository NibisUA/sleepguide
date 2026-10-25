import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Modal } from "../../components/Modal";
import { QueryError, Skeleton } from "../../components/QueryState";
import { api } from "../../lib/api";
import { useNow } from "../../lib/useNow";
import { WriteError } from "../records/WriteError";
import { useMe } from "../profile/api";
import { PlanForm } from "./PlanForm";
import { stats, usePlans, useStudyMutation, type Event, type Item, type Plan, type Replan } from "./api";

function Checklist({ plan, rows, disabled, onCheck }: { plan: Plan; rows: Item[]; disabled: boolean; onCheck: (plan: Plan, item: Item) => void }) {
  return <ul className="divide-y divide-muted/10">{rows.map(item => <li key={item.label}><label className="flex min-h-12 items-center gap-3 py-2">
    <input type="checkbox" className="h-5 w-5 shrink-0 accent-primary" checked={!!item.done_at} disabled={disabled} onChange={() => onCheck(plan, item)} aria-label={`${plan.name}: питання ${item.label}`} />
    <span className={`min-w-0 flex-1 break-words text-sm ${item.done_at ? "text-muted line-through" : ""}`}>{item.label}{item.title ? ` · ${item.title}` : ""}<span className="mt-1 block text-xs text-muted">{item.group}{item.group ? " · " : ""}Вага {item.weight}</span></span>
  </label></li>)}</ul>;
}

function ReplanSheet({ plan, onClose }: { plan: Plan; onClose: () => void }) {
  const preview = useQuery({ queryKey: ["study", plan.id, "replan", plan.version], queryFn: () => api<Replan>(`/study/plans/${plan.id}/replan-preview`) });
  const [edited, setEdited] = useState<Record<string, string | null> | null>(null);
  const save = useStudyMutation((value: Replan) => api<Plan>(`/study/plans/${plan.id}/schedule`, { method: "POST", body: JSON.stringify(value) }));
  const assignments = edited ?? preview.data?.assignments ?? {};
  return <Modal title="Перепланувати невиконане" onClose={() => { if (!save.isPending) onClose(); }}>
    <h2 className="text-lg font-semibold">Перепланувати невиконане</h2><p className="mt-2 text-sm text-muted">Від сьогодні до початку запасу. Виконані питання та історія збережуться. Дати можна змінити перед підтвердженням.</p>
    {preview.isPending ? <Skeleton /> : preview.isError ? <QueryError error={preview.error} retry={() => void preview.refetch()} /> : <>
      {Object.values(assignments).some(value => !value) && <p role="alert" className="mt-3 text-sm text-warning">Немає доступних робочих днів. Частина питань залишиться без дати. Можеш повернутися й змінити дедлайн або запас.</p>}
      <ul className="mt-3 divide-y divide-muted/20">{Object.entries(assignments).map(([label, day]) => <li key={label} className="flex items-center justify-between gap-2 py-2"><span className="text-sm">{label}<span className="block text-xs text-muted">Було: {plan.items.find(row => row.label === label)?.scheduled_date ?? "без дати"}</span></span><input type="date" aria-label={`Нова дата ${label}`} className="min-w-0 max-w-44 rounded-xl border border-muted/30 bg-bg p-2 text-sm" value={day ?? ""} disabled={save.isPending} onChange={e => setEdited({ ...assignments, [label]: e.target.value || null })} /></li>)}</ul>
      <WriteError error={save.error} /><button type="button" className="mt-3 min-h-11 w-full rounded-xl bg-primary px-4 py-3 text-on-primary" disabled={save.isPending || !Object.keys(assignments).length} onClick={() => save.mutate({ ...preview.data!, assignments }, { onSuccess: onClose })}>Підтвердити новий розклад</button>
    </>}
    <button type="button" className="mt-2 min-h-11 w-full text-primary" disabled={save.isPending} onClick={onClose}>Скасувати</button>
  </Modal>;
}

function PlanDetails({ plan, busy, check }: { plan: Plan; busy: boolean; check: (plan: Plan, item: Item) => void }) {
  const [historyOpen, setHistoryOpen] = useState(false), [moving, setMoving] = useState(false), [selected, setSelected] = useState<string[]>([]), [day, setDay] = useState("");
  const history = useQuery({ queryKey: ["study", plan.id, "events", plan.version], queryFn: () => api<Event[]>(`/study/plans/${plan.id}/events`), enabled: historyOpen });
  const move = useStudyMutation(() => api<Plan>(`/study/plans/${plan.id}/schedule`, { method: "POST", body: JSON.stringify({ expected_version: plan.version, assignments: Object.fromEntries(plan.items.filter(row => !row.done_at).map(row => [row.label, selected.includes(row.label) ? day : row.scheduled_date])) }) }));
  const dates = [...new Set(plan.items.map(row => row.scheduled_date ?? ""))].sort();
  return <div className="mt-3 space-y-3">
    <div className="flex flex-wrap gap-4"><button type="button" className="min-h-11 text-sm text-primary" onClick={() => setMoving(!moving)}>Перенести питання</button><button type="button" className="min-h-11 text-sm text-primary" onClick={() => setHistoryOpen(!historyOpen)}>Історія прогресу</button></div>
    {moving && <div className="space-y-2 border-t border-muted/20 pt-2"><label className="block text-sm">Нова дата<input type="date" required className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3" value={day} onChange={e => setDay(e.target.value)} /></label><div className="flex flex-wrap gap-2">{plan.items.filter(row => !row.done_at).map(row => <label key={row.label} className="flex min-h-11 items-center gap-2 px-2 text-sm"><input type="checkbox" checked={selected.includes(row.label)} onChange={e => setSelected(e.target.checked ? [...selected, row.label] : selected.filter(label => label !== row.label))} />{row.label}</label>)}</div><button type="button" className="min-h-11 rounded-xl border border-primary/50 px-4 text-primary" disabled={!day || !selected.length || busy || move.isPending} onClick={() => move.mutate(undefined, { onSuccess: () => { setMoving(false); setSelected([]); } })}>Перенести вибрані ({selected.length})</button><WriteError error={move.error} /></div>}
    {dates.map(date => { const rows = plan.items.filter(row => (row.scheduled_date ?? "") === date); return <details key={date}><summary className="min-h-11 py-3 text-sm">{date || "Без дати"} · {rows.filter(row => row.done_at).length}/{rows.length} · вага {rows.reduce((sum, row) => sum+row.weight, 0)}</summary><Checklist plan={plan} rows={rows} disabled={busy || move.isPending} onCheck={check} /></details>; })}
    {historyOpen && <div className="border-t border-muted/20 pt-2"><p className="text-sm font-medium">Останні 500 змін</p>{history.isPending ? <Skeleton /> : history.isError ? <QueryError error={history.error} retry={() => void history.refetch()} /> : <ul className="mt-2 space-y-2 text-xs text-muted">{history.data.map(event => <li key={event.id}>{new Date(event.created_at).toLocaleString("uk-UA")} · {({ created: "Створено план", edited: "Оновлено план", completed: "Виконано", reopened: "Знято відмітку", replanned: "Змінено розклад" } as Record<string, string>)[event.kind] ?? event.kind}{event.detail.label ? ` · ${event.detail.label}` : ""}</li>)}</ul>}</div>}
  </div>;
}

export function Study() {
  const plans = usePlans(), me = useMe();
  const now = useNow(60000);
  const parts = new Intl.DateTimeFormat("en", { timeZone: me.data?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now);
  const part = (key: string) => parts.find(row => row.type === key)!.value;
  const localToday = `${part("year")}-${part("month")}-${part("day")}`;
  const [form, setForm] = useState<Plan | "new" | null>(null), [replanning, setReplanning] = useState<Plan | null>(null);
  const check = useMutation({ mutationFn: ({ plan, item }: { plan: Plan; item: Item }) => api<Plan>(`/study/plans/${plan.id}/items/${encodeURIComponent(item.label)}`, { method: "POST", body: JSON.stringify({ expected_version: plan.version, done: !item.done_at }) }), onSuccess: () => plans.refetch() });
  const onCheck = (plan: Plan, item: Item) => check.mutate({ plan, item });
  return <main className="mx-auto max-w-md space-y-4 p-4">
    <div className="flex items-center justify-between gap-2"><h1 className="text-xl font-semibold">Підготовка до дедлайнів</h1><button type="button" className="min-h-11 shrink-0 rounded-xl bg-primary px-3 text-sm text-on-primary" onClick={() => setForm("new")}>+ План</button></div>
    {plans.isPending ? <Skeleton /> : plans.isError ? <QueryError error={plans.error} retry={() => void plans.refetch()} /> : <>
      {!plans.data.length ? <p className="text-sm text-muted">Додай власний предмет або ціль. Потрібні лише назва, дедлайн і кількість питань.</p> : <section className="rounded-3xl bg-surface p-4"><h2 className="font-medium">Сьогодні · {localToday}</h2>
        {plans.data.some(plan => plan.items.some(row => row.scheduled_date && ((!row.done_at && row.scheduled_date <= localToday) || row.scheduled_date === localToday))) ? plans.data.map(plan => {
          const due = plan.items.filter(row => row.scheduled_date && ((!row.done_at && row.scheduled_date <= localToday) || row.scheduled_date === localToday)); return due.length ? <div key={plan.id} className="mt-3"><h3 className="text-sm font-medium">{plan.name}</h3><Checklist plan={plan} rows={due} disabled={check.isPending} onCheck={onCheck} />{due.some(row => row.scheduled_date! < localToday) && <p className="text-xs text-warning">Включено невиконане за попередні дні</p>}</div> : null;
        }) : <p className="mt-2 text-sm text-muted">На сьогодні немає невиконаних запланованих питань.</p>}
      </section>}
      <WriteError error={check.error} />
      {plans.data.map(plan => { const s = stats(plan, localToday); return <section key={plan.id} className="rounded-3xl bg-surface p-4">
        <h2 className="break-words font-medium">{plan.name}</h2><p className="mt-1 text-xs text-muted">Дедлайн {plan.deadline} · запас {plan.reserve_days} дн.</p>
        <p className="mt-3 text-lg font-semibold">{s.done} із {s.total} · {s.percent}%</p><progress aria-label={`Прогрес ${plan.name}`} value={s.done} max={s.total} className="mt-2 h-2 w-full accent-primary" />
        <p className="mt-2 text-sm text-muted">Залишилось {s.remaining} питань · до дедлайну {s.deadlineDays} дн. · робочих {s.days}</p>
        <p className="mt-1 text-sm">{s.status}{s.daily !== null && s.remaining > 0 ? ` · орієнтир ${s.daily} питань/день` : ""}</p>
        {plan.items.some(row => row.weight !== 1) && s.dailyWeight !== null && s.remaining > 0 && <p className="mt-1 text-xs text-muted">Орієнтир навантаження: {s.dailyWeight} одиниць складності/день. Кількість питань по днях може відрізнятися.</p>}
        {plan.items.some(row => !row.done_at && !row.scheduled_date) && <p className="mt-2 text-sm text-warning">Є нерозподілені питання — зміни налаштування або переплануй.</p>}
        <div className="mt-2 flex flex-wrap gap-x-4"><button type="button" className="min-h-11 text-sm text-primary" onClick={() => setForm(plan)}>Редагувати</button><button type="button" disabled={check.isPending || !s.remaining} className="min-h-11 text-sm text-primary disabled:opacity-50" onClick={() => setReplanning(plan)}>Перепланувати невиконане</button></div>
        <details><summary className="min-h-11 py-3 text-sm text-primary">Розклад і питання</summary><PlanDetails plan={plan} busy={check.isPending} check={onCheck} /></details>
      </section>; })}
    </>}
    {form && <PlanForm plan={form === "new" ? undefined : form} onClose={() => setForm(null)} />}
    {replanning && <ReplanSheet plan={replanning} onClose={() => setReplanning(null)} />}
  </main>;
}
