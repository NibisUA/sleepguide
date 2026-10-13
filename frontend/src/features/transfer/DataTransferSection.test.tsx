import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import i18n from "../../lib/i18n";
import { DataTransferSection } from "./DataTransferSection";

const mock = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../../lib/api", async original => ({ ...await original<typeof import("../../lib/api")>(), api: mock.api }));
const preview = { ready: 1, duplicates: 1, errors: 0, imported: 0, timezone: "Europe/Kyiv", rows: [
  { line: 2, date: "2026-09-26", summary: "23:30 → 07:30 · 480 min", status: "ready", code: null },
  { line: 3, date: "2026-09-27", summary: "01:00 → 09:00 · 480 min", status: "duplicate", code: "csv_duplicate" },
] };
beforeEach(async () => {
  await i18n.changeLanguage("en"); mock.api.mockReset();
  mock.api.mockImplementation(async (path: string) => path === "/data/import" ? { ...preview, imported: 1 } : preview);
  URL.createObjectURL = vi.fn(() => "blob:csv"); URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
});
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><DataTransferSection /></QueryClientProvider>);
}
async function paste(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Paste CSV text" }));
  await user.type(screen.getByLabelText("CSV"), "date,bedtime,wake_time\n2026-09-26,23:30,07:30");
}

it("previews without writing, then imports only after explicit confirmation", async () => {
  const user = userEvent.setup(); mount(); await paste(user);
  expect(screen.queryByRole("button", { name: /Import \d/ })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Preview import" }));
  expect(await screen.findByText("Already exists — skipped")).toBeTruthy();
  expect(mock.api.mock.calls.some(([path]) => path === "/data/import")).toBe(false);
  await user.click(screen.getByRole("button", { name: "Import 1 entries" }));
  expect(await screen.findByText("Saved 1 entries to history.")).toBeTruthy();
  expect(mock.api).toHaveBeenCalledWith("/data/import", { method: "POST", body: JSON.stringify({ kind: "sleep", csv: "date,bedtime,wake_time\n2026-09-26,23:30,07:30" }) });
});

it("blocks import if any row is invalid", async () => {
  mock.api.mockResolvedValue({ ...preview, errors: 1, rows: [{ ...preview.rows[0], status: "error", code: "csv_time" }] });
  const user = userEvent.setup(); mount(); await paste(user);
  await user.click(screen.getByRole("button", { name: "Preview import" }));
  expect(await screen.findByText("Use HH:MM for times, for example 23:30.")).toBeTruthy();
  expect((screen.getByRole("button", { name: "Import 1 entries" }) as HTMLButtonElement).disabled).toBe(true);
});

it("invalidates the old preview when the CSV changes", async () => {
  const user = userEvent.setup(); mount(); await paste(user);
  await user.click(screen.getByRole("button", { name: "Preview import" }));
  await screen.findByRole("button", { name: "Import 1 entries" });
  await user.type(screen.getByLabelText("CSV"), "\n2026-09-27,00:00,08:00");
  expect(screen.queryByRole("button", { name: "Import 1 entries" })).toBeNull();
});

it("exports the selected diary as a CSV download", async () => {
  mock.api.mockResolvedValue({ filename: "sleepguide-screen.csv", csv: "\ufeffДата,total_minutes\n26.09.2026,240\n" });
  const user = userEvent.setup(); mount();
  await user.selectOptions(screen.getByLabelText("Data type"), "screen");
  await user.click(screen.getByRole("button", { name: "Export CSV" }));
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/data/export/screen"));
  expect(await screen.findByText("CSV is ready to download.")).toBeTruthy();
  expect(URL.createObjectURL).toHaveBeenCalled();
});
