import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useNow } from "../../lib/useNow";
import type { Progress } from "../../types/api";
import { useMe } from "../profile/api";

export const PROGRESS_KEY = ["progress"] as const;
export function useProgress() {
  const me = useMe();
  const now = useNow(60_000);
  const timezone = me.data?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
  const day = new Intl.DateTimeFormat("en-CA", { timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
  return useQuery({ queryKey: [...PROGRESS_KEY, timezone, day], queryFn: () => api<Progress>("/progress") });
}
