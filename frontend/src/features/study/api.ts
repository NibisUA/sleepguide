import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";

export interface Item { label: string; title: string; group: string; weight: number; scheduled_date: string | null; done_at?: string | null }
export interface PlanInput { name: string; deadline: string; start_date: string; total: number; reserve_days: number; daily_capacity: number | null; items?: Item[]; preserve_schedule: boolean; expected_version?: number }
export interface Plan extends Omit<PlanInput, "items" | "total" | "preserve_schedule" | "expected_version"> { id: number; items: Item[]; version: number; created_at: string }
export interface Parsed { name: string; deadline: string | null; start_date: string | null; total: number; declared_total: number | null; reserve_days: number; reserve_dates: string[]; items: Item[]; preserve_schedule: boolean; issues: { line: number; message: string }[] }
export interface Replan { expected_version: number; assignments: Record<string, string | null>; summary: { status: string } }
export interface Event { id: number; kind: string; detail: { label?: string; total?: number; changes?: unknown[] }; created_at: string }

export function usePlans() { return useQuery({ queryKey: ["study"], queryFn: () => api<Plan[]>("/study/plans") }); }
export function useStudyMutation<T, V>(action: (value: V) => Promise<T>) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: action, onSuccess: () => qc.invalidateQueries({ queryKey: ["study"] }) });
}
export const savePlan = (input: PlanInput, id?: number) => api<Plan>(id ? `/study/plans/${id}` : "/study/plans", { method: id ? "PUT" : "POST", body: JSON.stringify(input) });
export const parseText = (text: string, year: number | null) => api<Parsed>("/study/parse", { method: "POST", body: JSON.stringify({ text, year }) });
export const previewPlan = (input: PlanInput, id?: number) => api<{ items: Item[]; working_days: number }>(`/study/preview${id ? `?plan_id=${id}` : ""}`, { method: "POST", body: JSON.stringify(input) });
export function stats(plan: Plan, today: string) {
  const pending = plan.items.filter(row => !row.done_at), done = plan.items.length-pending.length;
  const workEnd = shiftDay(plan.deadline, -plan.reserve_days);
  const workStart = plan.start_date > today ? plan.start_date : today;
  const days = Math.max(0, Math.round((Date.parse(workEnd)-Date.parse(workStart))/86400000));
  const weight = pending.reduce((sum, row) => sum+row.weight, 0);
  return { done, total: plan.items.length, remaining: pending.length, days,
    deadlineDays: Math.max(0, Math.round((Date.parse(plan.deadline)-Date.parse(today))/86400000)),
    percent: plan.items.length ? Math.round(done*100/plan.items.length) : 0,
    daily: days ? Math.ceil(pending.length/days) : null,
    dailyWeight: days ? Math.ceil(weight/days) : null,
    status: !pending.length ? "Виконано" : today > plan.deadline ? "Дедлайн минув" : !days ? "Робочих днів не залишилося" : plan.daily_capacity && (weight > days*plan.daily_capacity || pending.some(row => row.weight > plan.daily_capacity!)) ? "Навантаження перевищує денний ліміт" : "У роботі",
  };
}
export function shiftDay(value: string, days: number) { const date = new Date(`${value}T12:00:00Z`); date.setUTCDate(date.getUTCDate()+days); return date.toISOString().slice(0, 10); }
export function itemsText(items: Item[]) { return items.map(row => [row.label, row.scheduled_date ?? "", row.weight, row.group, row.title].join(" | ")).join("\n"); }
export function textItems(text: string): Item[] {
  return text.split(/\r?\n/).filter(line => line.trim()).map((line, index) => {
    const [label, day = "", weight = "1", group = "", title = "", ...extra] = line.split("|").map(value => value.trim());
    const normalized = label.toUpperCase().replaceAll("Н", "N");
    if (extra.length || !/^(?:N\d+\.)?[1-9]\d*$/.test(normalized) || !/^\d+$/.test(weight) || Number(weight) < 1 || Number(weight) > 100 || (day && (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Number.isFinite(Date.parse(day)) || new Date(day).toISOString().slice(0, 10) !== day))) throw new Error(`Перевір рядок ${index+1}: номер | дата YYYY-MM-DD або порожньо | складність 1–100 | група | назва`);
    return { label: normalized, scheduled_date: day || null, weight: Number(weight), group, title };
  });
}
