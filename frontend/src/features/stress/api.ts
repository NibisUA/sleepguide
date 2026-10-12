import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { StressCategory, StressDay, StressLevel, StressLog } from "../../types/api";

export const STRESS_KEY = ["stress"] as const;

/** Per-day count / average / max between two YYYY-MM-DD dates (every day is present). */
export function useStressHistory(from: string, to: string) {
  return useQuery({
    queryKey: [...STRESS_KEY, "history", from, to],
    queryFn: () => api<StressDay[]>(`/stress/history?from=${from}&to=${to}`),
  });
}

export function useStressList(from: string, to: string, limit = 200) {
  return useQuery({
    queryKey: [...STRESS_KEY, "list", from, to, limit],
    queryFn: () => api<StressLog[]>(`/stress?from=${from}&to=${to}&limit=${limit}`),
  });
}

function useInvalidateStress() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: STRESS_KEY });
}

export interface StressInput {
  level: StressLevel;
  category?: StressCategory | null;
  logged_at?: string; // ISO; defaults to "now" on the server
}

export function useLogStress() {
  const invalidate = useInvalidateStress();
  return useMutation({
    mutationFn: (body: StressInput) =>
      api<StressLog>("/stress", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useUpdateStress() {
  const invalidate = useInvalidateStress();
  return useMutation({
    // `category: null` clears the category; an omitted field keeps its value.
    mutationFn: ({ id, ...body }: Partial<StressInput> & { id: number }) =>
      api<StressLog>(`/stress/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useDeleteStress() {
  const invalidate = useInvalidateStress();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/stress/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}
