import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { User } from "../../types/api";
import { SLEEP_KEY } from "../sleep/api";

export function useMe(enabled = true) {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/me"),
    enabled,
  });
}

type UserPatch = Partial<
  Pick<
    User,
    | "language"
    | "timezone"
    | "sleep_goal_minutes"
    | "target_bedtime"
    | "reminder_evening_time"
    | "reminder_morning_on"
    | "reminder_pattern_on"
    | "weekly_sleep_days"
    | "weekly_workout_days"
    | "weekly_stress_days"
    | "weekly_screen_days"
  >
>;

/** PATCH /me. `target_bedtime: null` clears the target. */
export function useUpdateMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: UserPatch) =>
      api<User>("/me", { method: "PATCH", body: JSON.stringify(patch) }),
    onSuccess: (user) => {
      qc.setQueryData(["me"], user);
      // Scores and charts depend on the goal, the bedtime target and the time zone.
      void qc.invalidateQueries({ queryKey: SLEEP_KEY });
    },
  });
}
