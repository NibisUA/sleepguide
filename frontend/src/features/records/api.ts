import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { components } from "../../types/api.gen";
import type { Exercise, ExerciseLog, ExerciseRecords } from "../../types/api";

type S = components["schemas"];
export type MetricsInput = S["ExerciseMetricsIn"];
export const RECORDS_KEY = ["records"] as const;
export const EXERCISES_KEY = ["exercises"] as const;
export const EXERCISE_LOGS_KEY = ["exercise-logs"] as const;

export function useExercises() {
  return useQuery({ queryKey: EXERCISES_KEY, queryFn: () => api<Exercise[]>("/exercises") });
}
export function useRecords() {
  return useQuery({ queryKey: RECORDS_KEY, queryFn: () => api<ExerciseRecords[]>("/records") });
}
export function useExerciseLogs(workoutId: number) {
  return useQuery({ queryKey: [...EXERCISE_LOGS_KEY, workoutId],
    queryFn: () => api<ExerciseLog[]>(`/workouts/${workoutId}/exercises`) });
}
function useInvalidate() {
  const qc = useQueryClient();
  return () => Promise.all([
    qc.invalidateQueries({ queryKey: RECORDS_KEY }),
    qc.invalidateQueries({ queryKey: EXERCISES_KEY }),
    qc.invalidateQueries({ queryKey: EXERCISE_LOGS_KEY }),
  ]);
}
export function useCreateExercise() {
  return useMutation({ mutationFn: (body: S["ExerciseCreateIn"]) => api<Exercise>("/exercises", {
    method: "POST", body: JSON.stringify(body) }), onSuccess: useInvalidate() });
}
export function useRenameExercise() {
  return useMutation({ mutationFn: ({ id, name }: { id: number; name: string }) => api<Exercise>(`/exercises/${id}`, {
    method: "PATCH", body: JSON.stringify({ name }) }), onSuccess: useInvalidate() });
}
export function useDeleteExercise() {
  return useMutation({ mutationFn: (id: number) => api<void>(`/exercises/${id}`, { method: "DELETE" }), onSuccess: useInvalidate() });
}
export function useSaveLog(workoutId: number) {
  return useMutation({ mutationFn: ({ id, exercise_id, ...metrics }: MetricsInput & { id?: number; exercise_id: number }) =>
    id ? api<ExerciseLog>(`/exercise-logs/${id}`, { method: "PUT", body: JSON.stringify(metrics) })
      : api<ExerciseLog>(`/workouts/${workoutId}/exercises`, { method: "POST", body: JSON.stringify({ exercise_id, ...metrics }) }),
    onSuccess: useInvalidate() });
}
export function useDeleteLog() {
  return useMutation({ mutationFn: (id: number) => api<void>(`/exercise-logs/${id}`, { method: "DELETE" }), onSuccess: useInvalidate() });
}
