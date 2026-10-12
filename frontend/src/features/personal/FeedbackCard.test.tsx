import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { FeedbackCard } from "./FeedbackCard";
import i18n from "../../lib/i18n";
const mocks = vi.hoisted(() => ({ mutate: vi.fn(), refetch: vi.fn(), query: {data: null as {rating: number} | null, isPending:false, isError:false}, pending:false }));
vi.mock("./api", () => ({useFeedback: () => ({...mocks.query,refetch:mocks.refetch}), useSaveFeedback: () => ({mutate:mocks.mutate,isPending:mocks.pending,isError:false})}));
beforeEach(async () => { await i18n.changeLanguage("uk"); mocks.query={data:null,isPending:false,isError:false}; mocks.pending=false; mocks.mutate.mockClear(); });
it("shows the saved rating and lets the user replace or delete it", async () => {
  mocks.query.data={rating:4};
  render(<FeedbackCard day="2026-10-11" />);
  expect(screen.getByRole("button",{name:/4 —/}).getAttribute("aria-pressed")).toBe("true");
  await userEvent.click(screen.getByRole("button",{name:/3 —/}));
  expect(mocks.mutate).toHaveBeenLastCalledWith(3);
  await userEvent.click(screen.getByRole("button",{name:/Видалити ранкову/}));
  expect(mocks.mutate).toHaveBeenLastCalledWith(null);
});
it("does not accept a rating before the previous value loads", () => {
  mocks.query.isPending=true;
  render(<FeedbackCard day="2026-10-11" />);
  expect(screen.getByRole("button",{name:/4 —/}).hasAttribute("disabled")).toBe(true);
});
