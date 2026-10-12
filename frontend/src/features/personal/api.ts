import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useNow } from "../../lib/useNow";
import { useMe } from "../profile/api";
import type { Baselines, Calibration, Feedback, Milestones } from "../../types/api";

export const PERSONAL_KEY = ["personal"] as const;
function usePersonal<T>(kind: string) {
  const me = useMe();
  const now = useNow(60_000);
  const timezone = me.data?.timezone ?? "UTC";
  const day = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
  return useQuery({ queryKey: [...PERSONAL_KEY, kind, timezone, day], queryFn: () => api<T>(`/personal/${kind}`) });
}
export function useBaselines() { return usePersonal<Baselines>("baselines"); }
export function useMilestones() { return usePersonal<Milestones>("milestones"); }
export function useCalibration() { return usePersonal<Calibration>("calibration"); }
export function useFeedback(day: string) {
  return useQuery({ queryKey: [...PERSONAL_KEY, "feedback", day], queryFn: () => api<Feedback | null>(`/personal/feedback/${day}`) });
}
export function useSaveFeedback(day: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (rating: number | null) => api<Feedback | void>(`/personal/feedback/${day}`,
    rating === null ? { method: "DELETE" } : { method: "PUT", body: JSON.stringify({ rating }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: PERSONAL_KEY }) });
}
