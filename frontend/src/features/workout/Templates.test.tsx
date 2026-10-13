import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import i18n from "../../lib/i18n";
import { Templates, SaveTemplate } from "./Templates";
import { ExerciseLogsSheet } from "../records/ExerciseLogsSheet";
import type { Workout } from "../../types/api";

const mock = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../../lib/api", async original => ({ ...await original<typeof import("../../lib/api")>(), api: mock.api }));
const stamp = "2026-10-10T12:00:00Z";
const workout: Workout = { id: 5, started_at: stamp, ended_at: "2026-10-10T14:00:00Z", local_date: "2026-10-10", duration_minutes: 120, type: "gym", intensity: "moderate", source: "manual" };
const sets = [{ exercise_id: 1, weight_kg: "80.50", reps: 5, distance_m: null, duration_seconds: null }];
beforeEach(async () => {
  await i18n.changeLanguage("en"); mock.api.mockReset();
  mock.api.mockImplementation(async (path: string, init?: RequestInit) => {
    if (init?.method) return workout;
    if (path === "/workout-templates") return [{ id: 1, name: "Upper body", type: "gym", intensity: "moderate", sets }];
    if (path === "/exercises") return [{ id: 1, name: "Bench press", kind: "strength" }];
    if (path.includes("/exercises")) return [];
    return [workout];
  });
});
function mount(element: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={qc}>{element}</QueryClientProvider>);
}

it("starts the selected saved plan", async () => {
  mount(<Templates />); const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Start from template" }));
  expect(mock.api).toHaveBeenCalledWith("/workout-templates/1/start", { method: "POST" });
});

it("repeats the latest completed workout", async () => {
  mount(<Templates />); const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Repeat last workout" }));
  expect(mock.api).toHaveBeenCalledWith("/workouts/5/repeat", { method: "POST" });
});

it("saves a named routine from a completed workout", async () => {
  mount(<SaveTemplate workout={workout} />); const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Save as template" }));
  await user.type(screen.getByLabelText("Template name"), "Upper body");
  await user.click(screen.getByRole("button", { name: "Save as template" }));
  expect(mock.api).toHaveBeenCalledWith("/workout-templates", { method: "POST", body: '{"name":"Upper body","workout_id":5}' });
});

it("only prefills a plan target, then saves the adjusted actual result", async () => {
  mount(<ExerciseLogsSheet workout={{ ...workout, planned_sets: sets }} onClose={vi.fn()} />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Use for a new set" }));
  expect((screen.getByLabelText("Weight, kg") as HTMLInputElement).value).toBe("80.50");
  expect(mock.api.mock.calls.filter(([, init]) => init?.method)).toHaveLength(0);
  await user.clear(screen.getByLabelText("Reps")); await user.type(screen.getByLabelText("Reps"), "4");
  await user.click(screen.getByRole("button", { name: "Save result" }));
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/workouts/5/exercises", { method: "POST", body: '{"exercise_id":1,"weight_kg":"80.50","reps":4}' }));
});
