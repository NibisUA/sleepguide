import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../lib/api";
import i18n from "../../lib/i18n";
import type { HistoryEntries, HistoryOverview } from "../../types/api";
import { History } from "./History";
import type { HistoryRange } from "./api";

const mock = vi.hoisted(() => ({ api: vi.fn(), failNext: false }));
vi.mock("../../lib/api", async importOriginal => ({ ...await importOriginal<typeof import("../../lib/api")>(), api: mock.api }));
vi.mock("./YearHeatmap", () => ({ YearHeatmap: () => <div>Calendar</div> }));

function overview(range: HistoryRange): HistoryOverview {
  return { range, from_date: range === "all" ? "2020-01-01" : "2026-09-01", to_date: "2026-10-12",
    days: range === "all" ? 2477 : range === "90d" ? 90 : range === "30d" ? 30 : 7,
    bucket_days: range === "all" ? 28 : 1, has_data: true,
    sleep: { days: 450, average_minutes: 480, average_score: 85, nap_minutes: 0 },
    workout: { count: 222, minutes: 2220 }, stress: { count: 333, average: 2.6, peak: 5 },
    screen: { days: 444, average_total: 240, average_before_bed: 20 },
    points: [{ date: "2026-10-12", end_date: "2026-10-12", sleep_minutes: 480, score: 85,
      workout_count: 2, workout_minutes: 20, stress_count: 3, stress_average: 2, stress_max: 5,
      screen_total: 100, screen_before_bed: null }] };
}
function page(kind: string, next: boolean): HistoryEntries {
  const result: HistoryEntries = { kind: kind as HistoryEntries["kind"], sleep_sessions: [], workouts: [], stress_logs: [], screen_time: [], next_cursor: kind === "workout" && !next ? "next-page" : null };
  if (kind === "workout") result.workouts = [{ id: next ? 2 : 1, started_at: "2026-10-10T12:00:00Z", ended_at: "2026-10-10T13:00:00Z", local_date: "2026-10-10", duration_minutes: next ? 99 : 10, type: "gym", intensity: "easy", source: "retro" }];
  return result;
}
beforeEach(async () => {
  await i18n.changeLanguage("en"); mock.api.mockReset(); mock.failNext = false;
  mock.api.mockImplementation(async (path: string) => {
    if (path === "/me") return { timezone: "Europe/Kyiv", language: "en", sleep_goal_minutes: 480 };
    if (path.startsWith("/history?")) return overview(new URLSearchParams(path.split("?")[1]).get("range") as HistoryRange);
    if (path.startsWith("/history/entries/")) {
      const kind = path.split("/")[3].split("?")[0];
      const next = path.includes("cursor=");
      if (next && mock.failNext) throw new ApiError(0, "network_error");
      return page(kind, next);
    }
    return [];
  });
});
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><History /></QueryClientProvider>);
}

it("switches to 90 days and all time with named pressed controls and explicit grouping", async () => {
  const user = userEvent.setup(); mount();
  await user.click(screen.getByRole("button", { name: "90 days" }));
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/history?range=90d"));
  expect(screen.getByRole("button", { name: "90 days" }).getAttribute("aria-pressed")).toBe("true");
  await user.click(screen.getByRole("button", { name: "All time" }));
  await screen.findByText("Each point spans up to 28 days. Summaries include every entry.");
  expect(mock.api).toHaveBeenCalledWith("/history?range=all");
  expect(screen.getByRole("button", { name: "All time" }).getAttribute("aria-pressed")).toBe("true");
});

it("loads older entries while totals continue to cover the entire period", async () => {
  const user = userEvent.setup(); mount();
  const more = await screen.findByRole("button", { name: "Load more: workouts" });
  const section = screen.getByRole("heading", { name: i18n.t("workout.historyTitle") }).closest("section")!;
  expect(within(section).getByText("222")).toBeTruthy();
  expect(within(section).getByText("37h 0m")).toBeTruthy();
  await user.click(more);
  await waitFor(() => expect(within(section).getAllByRole("button", { name: "Exercises" }).length).toBe(2));
  expect(within(section).getByText("222")).toBeTruthy();
  expect(within(section).queryByRole("button", { name: "Load more: workouts" })).toBeNull();
});

it("keeps already loaded records visible and permits retry after a page error", async () => {
  const user = userEvent.setup(); mount(); mock.failNext = true;
  await user.click(await screen.findByRole("button", { name: "Load more: workouts" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Cannot reach the server");
  const section = screen.getByRole("heading", { name: i18n.t("workout.historyTitle") }).closest("section")!;
  expect(within(section).getAllByRole("button", { name: "Exercises" }).length).toBe(1);
  mock.failNext = false;
  await user.click(within(section).getByRole("button", { name: "Try again" }));
  await waitFor(() => expect(within(section).getAllByRole("button", { name: "Exercises" }).length).toBe(2));
});
