import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { SleepSession } from "../../types/api";

const SLEEP_KEY = ["sleep"] as const;

export function useCurrentSleep() {
  return useQuery({
    queryKey: [...SLEEP_KEY, "current"],
    queryFn: () => api<SleepSession | null>("/sleep/current"),
  });
}

export function useSleepList(limit = 7) {
  return useQuery({
    queryKey: [...SLEEP_KEY, "list", limit],
    queryFn: () => api<SleepSession[]>(`/sleep?limit=${limit}`),
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
