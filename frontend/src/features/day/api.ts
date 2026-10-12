import { useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { DaySummary } from "../../types/api";

/** Every successful mutation invalidates this prefix (see the MutationCache in App.tsx). */
export const DAYS_KEY = ["days"] as const;

export function useDaySummary(date: string) {
  return useQuery({
    queryKey: [...DAYS_KEY, date],
    queryFn: () => api<DaySummary>(`/days/${date}`),
  });
}
