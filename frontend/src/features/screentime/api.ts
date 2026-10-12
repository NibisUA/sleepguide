import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { ScreenTime } from "../../types/api";

export const SCREEN_KEY = ["screen-time"] as const;

/** Records between two YYYY-MM-DD dates; days without data are simply absent. */
export function useScreenTimeRange(from: string, to: string, enabled = true) {
  return useQuery({
    queryKey: [...SCREEN_KEY, "range", from, to],
    queryFn: () => api<ScreenTime[]>(`/screen-time?from=${from}&to=${to}`),
    enabled,
  });
}

function useInvalidateScreenTime() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: SCREEN_KEY });
}

export interface ScreenTimeInput {
  date: string; // YYYY-MM-DD, the local day the numbers refer to
  total_minutes: number;
  before_bed_minutes: number | null;
}

/** Idempotent upsert: saving the same day again replaces it. */
export function usePutScreenTime() {
  const invalidate = useInvalidateScreenTime();
  return useMutation({
    mutationFn: ({ date, ...body }: ScreenTimeInput) =>
      api<ScreenTime>(`/screen-time/${date}`, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useDeleteScreenTime() {
  const invalidate = useInvalidateScreenTime();
  return useMutation({
    mutationFn: (date: string) => api<void>(`/screen-time/${date}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}
