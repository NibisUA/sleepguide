import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Workout, WorkoutDay, WorkoutIntensity, WorkoutType } from "../../types/api";

export const WORKOUT_KEY = ["workouts"] as const;

export function useCurrentWorkout() {
  return useQuery({
    queryKey: [...WORKOUT_KEY, "current"],
    queryFn: () => api<Workout | null>("/workouts/current"),
  });
}

/** Per-day count and minutes between two YYYY-MM-DD dates (every day is present). */
export function useWorkoutHistory(from: string, to: string) {
  return useQuery({
    queryKey: [...WORKOUT_KEY, "history", from, to],
    queryFn: () => api<WorkoutDay[]>(`/workouts/history?from=${from}&to=${to}`),
  });
}

export function useWorkoutList(from: string, to: string, limit = 100) {
  return useQuery({
    queryKey: [...WORKOUT_KEY, "list", from, to, limit],
    queryFn: () => api<Workout[]>(`/workouts?from=${from}&to=${to}&limit=${limit}`),
  });
}

function useInvalidateWorkouts() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: WORKOUT_KEY });
}

export function useStartWorkout() {
  const invalidate = useInvalidateWorkouts();
  return useMutation({
    mutationFn: (body: { type: WorkoutType; intensity: WorkoutIntensity }) =>
      api<Workout>("/workouts/start", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export interface StopWorkoutInput {
  ended_at?: string; // required if the workout has run for more than 6 hours
  type?: WorkoutType;
  intensity?: WorkoutIntensity;
}

export function useStopWorkout() {
  const invalidate = useInvalidateWorkouts();
  return useMutation({
    mutationFn: (body: StopWorkoutInput) =>
      api<Workout>("/workouts/stop", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export interface WorkoutFormValues {
  started_at: string; // ISO strings
  ended_at: string;
  type: WorkoutType;
  intensity: WorkoutIntensity;
}

export function useCreateWorkout() {
  const invalidate = useInvalidateWorkouts();
  return useMutation({
    mutationFn: (body: WorkoutFormValues) =>
      api<Workout>("/workouts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useUpdateWorkout() {
  const invalidate = useInvalidateWorkouts();
  return useMutation({
    mutationFn: ({ id, ...body }: WorkoutFormValues & { id: number }) =>
      api<Workout>(`/workouts/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: invalidate,
  });
}

export function useDeleteWorkout() {
  const invalidate = useInvalidateWorkouts();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/workouts/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}
