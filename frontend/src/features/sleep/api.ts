import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { SleepDay, SleepScore, SleepSession } from "../../types/api";

export const SLEEP_KEY = ["sleep"] as const;

export function useCurrentSleep() {
  return useQuery({
    queryKey: [...SLEEP_KEY, "current"],
    queryFn: () => api<SleepSession | null>("/sleep/current"),
  });
}

export function useSleepList(limit = 7, date?: string) {
  const query = date ? `limit=${limit}&date=${date}` : `limit=${limit}`;
  return useQuery({
    queryKey: [...SLEEP_KEY, "list", limit, date ?? null],
    queryFn: () => api<SleepSession[]>(`/sleep?${query}`),
  });
}

/** Sleep Score + component breakdown for the night ending on `date`. */
export function useSleepScore(date?: string) {
  return useQuery({
    queryKey: [...SLEEP_KEY, "score", date ?? null],
    queryFn: () => api<SleepScore | null>(`/sleep/score/${date}`),
    enabled: Boolean(date),
  });
}

/** Aggregated days between two YYYY-MM-DD dates (charts, heatmap). */
export function useSleepHistory(from: string, to: string) {
  return useQuery({
    queryKey: [...SLEEP_KEY, "history", from, to],
    queryFn: () => api<SleepDay[]>(`/sleep/history?from=${from}&to=${to}`),
  });
}

export function useStartSleep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<SleepSession>("/sleep/start", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: SLEEP_KEY }),
  });
}

export function useStopSleep() {
  const qc = useQueryClient();
  return useMutation({
    // `endedAt` (ISO string) is required if the session was open for more than 14 hours.
    mutationFn: (endedAt?: string) =>
      api<SleepSession>("/sleep/stop", {
        method: "POST",
        body: JSON.stringify(endedAt ? { ended_at: endedAt } : {}),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: SLEEP_KEY }),
  });
}

/** Retroactive entry: a completed sleep logged after the fact. */
export function useCreateSleep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { started_at: string; ended_at: string }) =>
      api<SleepSession>("/sleep", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: SLEEP_KEY }),
  });
}

export function useUpdateSleep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; started_at?: string; ended_at?: string }) =>
      api<SleepSession>(`/sleep/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: SLEEP_KEY }),
  });
}

export function useDeleteSleep() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/sleep/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: SLEEP_KEY }),
  });
}
