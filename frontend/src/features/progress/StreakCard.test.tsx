import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import i18n from "../../lib/i18n";
import { StreakCard } from "./StreakCard";

const mock = vi.hoisted(() => ({ useProgress: vi.fn() }));
vi.mock("./api", () => mock);
beforeEach(async () => { await i18n.changeLanguage("en"); });

it("keeps yesterday's streak active while today is open and explains categories", async () => {
  mock.useProgress.mockReturnValue({ data: { streaks: [
    { kind: "all", current: 6, longest: 10, counted_today: false },
    { kind: "workout", current: 0, longest: 3, counted_today: false },
  ] }, isPending: false, isError: false });
  render(<QueryClientProvider client={new QueryClient()}><StreakCard /></QueryClientProvider>);
  expect(screen.getByText("6 days")).toBeTruthy();
  expect(screen.getByText("Your streak continues. You still have today to add a log.")).toBeTruthy();
  await userEvent.setup().click(screen.getByText("Category streaks and rules"));
  expect(screen.getByText("Workouts")).toBeTruthy();
  expect(screen.getByText(/does not recommend daily training/)).toBeTruthy();
});

it("shows an encouraging empty state for a new account", () => {
  mock.useProgress.mockReturnValue({ data: { streaks: [{ kind: "all", current: 0, longest: 0, counted_today: false }] }, isPending: false, isError: false });
  render(<QueryClientProvider client={new QueryClient()}><StreakCard /></QueryClientProvider>);
  expect(screen.getByText("Each day with a log builds a fuller history.")).toBeTruthy();
});
