import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import i18n from "../../lib/i18n";
import { CategoryBreakdown } from "./CategoryBreakdown";
import { ScreenTimeForm } from "./ScreenTimeForm";
import { categoryDistribution } from "./categories";

vi.mock("./api", () => ({ useScreenTimeRange: () => ({ data: [], isPending: false, isError: false }) }));
beforeEach(async () => { await i18n.changeLanguage("en"); });

it("calculates the unassigned remainder without inventing missing category zeros", () => {
  expect(categoryDistribution(542, { social_minutes: 326, entertainment_minutes: 73, games_minutes: 53 })).toMatchObject({ sum: 452, remaining: 90, complete: true, valid: true });
  expect(categoryDistribution(100, { social_minutes: 0 })).toMatchObject({ sum: 0, remaining: 100, complete: false });
  render(<CategoryBreakdown total={100} categories={{ social_minutes: 0 }} />);
  expect(screen.getAllByText("—")).toHaveLength(2);
  expect(screen.getByText(/Unassigned/)).toBeTruthy();
});

it("saves category hours and minutes with the total", async () => {
  const user = userEvent.setup(), save = vi.fn();
  render(<ScreenTimeForm title="Test" initialDate="2026-10-11" records={[]} busy={false} error={null} onSubmit={save} onCancel={vi.fn()} />);
  const hours = screen.getAllByLabelText("Hours"), minutes = screen.getAllByLabelText("Minutes");
  await user.type(hours[0], "9"); await user.type(minutes[0], "2");
  await user.type(screen.getByLabelText("Social: Hours"), "5"); await user.type(screen.getByLabelText("Social: Minutes"), "26");
  await user.type(screen.getByLabelText("Entertainment: Hours"), "1"); await user.type(screen.getByLabelText("Entertainment: Minutes"), "13");
  await user.type(screen.getByLabelText("Games: Minutes"), "53");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(save).toHaveBeenCalledWith({ date: "2026-10-11", total_minutes: 542, before_bed_minutes: null, social_minutes: 326, entertainment_minutes: 73, games_minutes: 53 });
  expect(screen.getByText(/Other:/)).toBeTruthy();
});

it("rejects a breakdown exceeding the total", async () => {
  const user = userEvent.setup(), save = vi.fn();
  render(<ScreenTimeForm title="Test" initialDate="2026-10-11" records={[]} busy={false} error={null} onSubmit={save} onCancel={vi.fn()} />);
  await user.type(screen.getAllByLabelText("Minutes")[0], "30");
  await user.type(screen.getByLabelText("Social: Minutes"), "40");
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(save).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toContain("cannot exceed");
});
