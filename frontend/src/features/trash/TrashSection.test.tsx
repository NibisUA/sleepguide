import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../../lib/api";
import i18n from "../../lib/i18n";
import { TrashSection, UndoNotice } from "./TrashSection";

const mock = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../../lib/api", async original => ({ ...await original<typeof import("../../lib/api")>(), api: mock.api }));
const row = { id: 10, kind: "workout", record_id: 5, record_key: "5", label: "2026-10-10", deleted_at: "2026-10-10T12:00:00Z", expires_at: "2026-11-09T12:00:00Z" };
beforeEach(async () => { await i18n.changeLanguage("en"); mock.api.mockReset(); mock.api.mockImplementation(async (_path: string, init?: RequestInit) => init?.method ? undefined : [row]); });
function mount(element: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={qc}>{element}</QueryClientProvider>);
}
it("restores the selected entry from Trash", async () => {
  mount(<TrashSection />); const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Trash" }));
  await user.click(await screen.findByRole("button", { name: "Restore" }));
  expect(mock.api).toHaveBeenCalledWith("/trash/10/restore", { method: "POST" });
});
it("keeps the entry visible and explains a restore conflict", async () => {
  mock.api.mockImplementation(async (_path: string, init?: RequestInit) => { if (init?.method) throw new ApiError(409, "restore_conflict"); return [row]; });
  mount(<TrashSection />); const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Trash" }));
  await user.click(await screen.findByRole("button", { name: "Restore" }));
  expect((await screen.findByRole("alert")).textContent).toContain("remains in Trash");
  expect(screen.getByText("Workout · 2026-10-10")).toBeTruthy();
});
it("undo matches the deleted record even if another deletion is newer", async () => {
  mock.api.mockImplementation(async (_path: string, init?: RequestInit) => init?.method ? undefined : [{ ...row, id: 11, record_key: "6", record_id: 6 }, row]);
  mount(<UndoNotice />);
  act(() => { window.dispatchEvent(new CustomEvent("diary-deleted", { detail: { kind: "workout", recordId: "5" } })); });
  const user = userEvent.setup();
  await waitFor(() => expect((screen.getByRole("button", { name: "Undo" }) as HTMLButtonElement).disabled).toBe(false));
  await user.click(screen.getByRole("button", { name: "Undo" }));
  expect(mock.api).toHaveBeenCalledWith("/trash/10/restore", { method: "POST" });
  await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
});
