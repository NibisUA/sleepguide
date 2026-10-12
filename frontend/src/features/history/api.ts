import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useNow } from "../../lib/useNow";
import type { components } from "../../types/api.gen";
import type { HistoryEntries, HistoryOverview } from "../../types/api";
import { useMe } from "../profile/api";

export type HistoryRange = components["schemas"]["HistoryOverviewOut"]["range"];
export type HistoryKind = components["schemas"]["HistoryEntriesOut"]["kind"];
export const HISTORY_KEY = ["history"] as const;

export function useHistoryOverview(range: HistoryRange) {
  const me = useMe();
  const now = useNow(60_000);
  const day = new Intl.DateTimeFormat("en-CA", { timeZone: me.data?.timezone,
    year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
  return useQuery({ queryKey: [...HISTORY_KEY, "overview", range, day, me.data?.timezone],
    queryFn: () => api<HistoryOverview>(`/history?range=${range}`) });
}

export function useHistoryEntries(kind: HistoryKind, from?: string, to?: string) {
  return useInfiniteQuery({
    queryKey: [...HISTORY_KEY, "entries", kind, from, to],
    initialPageParam: null as string | null,
    enabled: Boolean(from && to),
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ from: from!, to: to!, limit: "30" });
      if (pageParam) params.set("cursor", pageParam);
      return api<HistoryEntries>(`/history/entries/${kind}?${params}`);
    },
    getNextPageParam: last => last.next_cursor ?? undefined,
  });
}

export function sleepPoints(overview: HistoryOverview) {
  return overview.points.map(point => ({ date: point.date, end_date: point.end_date,
    sleep_minutes: Math.round(point.sleep_minutes ?? 0), score: point.score }));
}
export function workoutPoints(overview: HistoryOverview) {
  return overview.points.map(point => ({ date: point.date, end_date: point.end_date,
    count: point.workout_count, minutes: point.workout_minutes }));
}
export function stressPoints(overview: HistoryOverview) {
  return overview.points.map(point => ({ date: point.date, end_date: point.end_date,
    average: point.stress_average, max: point.stress_max, count: point.stress_count }));
}
export function screenPoints(overview: HistoryOverview) {
  return overview.points.map(point => ({ date: point.date, end_date: point.end_date,
    total: point.screen_total === null ? null : Math.round(point.screen_total),
    beforeBed: point.screen_before_bed === null ? null : Math.round(point.screen_before_bed) }));
}
