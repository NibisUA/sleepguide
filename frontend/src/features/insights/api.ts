import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Insight, InsightsProgress } from "../../types/api";

export const INSIGHTS_KEY = ["insights"] as const;
export function useInsights() {
  return useQuery({ queryKey: [...INSIGHTS_KEY, "list"],
    queryFn: () => api<Insight[]>("/insights"), staleTime: 60_000 });
}
export function useInsightsProgress() {
  return useQuery({ queryKey: [...INSIGHTS_KEY, "progress"],
    queryFn: () => api<InsightsProgress>("/insights/progress"), staleTime: 60_000 });
}
