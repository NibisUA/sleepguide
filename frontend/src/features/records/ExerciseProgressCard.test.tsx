import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import i18n from "../../lib/i18n";
import type { ExerciseRecords, Record } from "../../types/api";
import { ExerciseProgressCard } from "./ExerciseProgressCard";

const record = (weight: number, reps: number): Record => ({ metric: "reps", value: reps, weight_kg: weight, reps, distance_m: null, duration_seconds: null, date: "2026-09-26", log_id: 1, workout_id: 7 });
it("compares reps at selected weight and opens the source workout", async () => {
  await i18n.changeLanguage("en"); const user = userEvent.setup(), open = vi.fn();
  const data: ExerciseRecords = { exercise: { id: 1, name: "Bench press", kind: "strength", created_at: "2026-09-26T12:00:00Z", updated_at: "2026-09-26T12:00:00Z" },
    records: [{ ...record(80, 6), metric: "weight", value: 80 }], rep_bests: [record(60, 12), record(80, 6)] };
  render(<ExerciseProgressCard data={data} onOpen={open}><button>Rename</button></ExerciseProgressCard>);
  expect((screen.getByLabelText("Compare reps at weight") as HTMLSelectElement).value).toBe("80");
  await user.selectOptions(screen.getByLabelText("Compare reps at weight"), "60");
  expect(screen.getByText("60 kg × 12")).toBeTruthy();
  await user.click(screen.getAllByRole("button", { name: /Open workout/ })[0]);
  expect(open).toHaveBeenCalledWith(7);
});
