import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../lib/api";
import i18n from "../../lib/i18n";
import type { Exercise, ExerciseLog, Workout } from "../../types/api";
import { ExerciseLogsSheet } from "./ExerciseLogsSheet";

const mock = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../../lib/api", async importOriginal => ({ ...await importOriginal<typeof import("../../lib/api")>(), api: mock.api }));
const timestamp = "2026-10-10T12:00:00Z";
const exercises: Exercise[] = [{ id: 1, name: "Bench press", kind: "strength", created_at: timestamp, updated_at: timestamp },
  { id: 2, name: "Running", kind: "cardio", created_at: timestamp, updated_at: timestamp }];
const workout: Workout = { id: 5, started_at: timestamp, ended_at: "2026-10-10T14:00:00Z", local_date: "2026-10-10", duration_minutes: 120, type: "gym", intensity: "moderate", source: "manual" };
let logs: ExerciseLog[];
beforeEach(async () => {
  logs = []; mock.api.mockReset(); await i18n.changeLanguage("en");
  mock.api.mockImplementation(async (path: string, init?: RequestInit) => {
    if (!init?.method) return path === "/exercises" ? exercises : logs;
    return { id: 7, ...JSON.parse(String(init.body)), workout_id: 5, created_at: timestamp, updated_at: timestamp };
  });
});
function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={qc}><ExerciseLogsSheet workout={workout} onClose={vi.fn()} /></QueryClientProvider>);
}

it("saves one strength set with decimal weight and repetitions", async () => {
  const user = userEvent.setup(); mount();
  await user.selectOptions(await screen.findByLabelText("Exercise"), "1");
  await user.type(screen.getByLabelText("Weight, kg"), "50.25");
  await user.type(screen.getByLabelText("Reps"), "8");
  await user.click(screen.getByRole("button", { name: "Save result" }));
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/workouts/5/exercises", { method: "POST", body: '{"exercise_id":1,"weight_kg":"50.25","reps":8}' }));
});

it("saves distance in meters and combines minutes and seconds exactly", async () => {
  const user = userEvent.setup(); mount();
  await user.selectOptions(await screen.findByLabelText("Exercise"), "2");
  await user.type(screen.getByLabelText("Distance, m"), "5000");
  await user.type(screen.getByLabelText("Minutes"), "24");
  await user.type(screen.getByLabelText("Seconds"), "35");
  await user.click(screen.getByRole("button", { name: "Save result" }));
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/workouts/5/exercises", { method: "POST", body: '{"exercise_id":2,"distance_m":5000,"duration_seconds":1475}' }));
});

it("edits an existing result and preserves its exercise", async () => {
  logs = [{ id: 7, workout_id: 5, exercise_id: 1, weight_kg: 60, reps: 8, distance_m: null, duration_seconds: null, created_at: timestamp, updated_at: timestamp }];
  const user = userEvent.setup(); mount();
  await user.click(await screen.findByRole("button", { name: "Edit" }));
  expect((screen.getByLabelText("Exercise") as HTMLSelectElement).disabled).toBe(true);
  await user.clear(screen.getByLabelText("Reps")); await user.type(screen.getByLabelText("Reps"), "10");
  await user.click(screen.getByRole("button", { name: "Save result" }));
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/exercise-logs/7", { method: "PUT", body: '{"weight_kg":"60","reps":10}' }));
});

it("retains entered results and shows a readable error when saving fails", async () => {
  mock.api.mockImplementation(async (path: string, init?: RequestInit) => {
    if (init?.method) throw new ApiError(422, "exercise_time");
    return path === "/exercises" ? exercises : [];
  });
  const user = userEvent.setup(); mount();
  await user.selectOptions(await screen.findByLabelText("Exercise"), "2");
  await user.type(screen.getByLabelText("Distance, m"), "5000");
  await user.type(screen.getByLabelText("Minutes"), "150");
  await user.click(screen.getByRole("button", { name: "Save result" }));
  expect((await screen.findByRole("alert")).textContent).toContain("exceeds the workout duration");
  expect((screen.getByLabelText("Distance, m") as HTMLInputElement).value).toBe("5000");
});

it("creates an exercise with the selected metric type", async () => {
  const user = userEvent.setup(); mount();
  await user.click(await screen.findByRole("button", { name: "New exercise" }));
  await user.type(screen.getByLabelText("Exercise name"), "Pull-ups");
  await user.click(screen.getByRole("button", { name: "Create exercise" }));
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/exercises", { method: "POST", body: '{"name":"Pull-ups","kind":"strength"}' }));
});

it("names every form control and has no detectable axe violations", async () => {
  const user = userEvent.setup(); mount(); document.documentElement.lang = "en";
  await user.selectOptions(await screen.findByLabelText("Exercise"), "2");
  const result = await axe.run(document.body, { rules: { "color-contrast": { enabled: false } } });
  expect(result.violations.map(issue => issue.id)).toEqual([]);
});
