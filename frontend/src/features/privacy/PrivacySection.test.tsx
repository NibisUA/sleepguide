import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { beforeEach, expect, it, vi } from "vitest";
import i18n from "../../lib/i18n";
import { PrivacySection } from "./PrivacySection";

const mock = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../../lib/api", () => ({ api: mock.api }));
beforeEach(async () => { mock.api.mockReset(); await i18n.changeLanguage("en"); });
function mount(onDeleted = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={qc}><main><h1>Settings</h1><PrivacySection onDeleted={onDeleted} /></main></QueryClientProvider>);
  return onDeleted;
}

it("requires confirmation and cancels without sending a delete request", async () => {
  const user = userEvent.setup(); mount();
  await user.click(screen.getByRole("button", { name: "Delete account and data" }));
  expect((screen.getByRole("button", { name: "Confirm deletion" }) as HTMLButtonElement).disabled).toBe(true);
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(mock.api).not.toHaveBeenCalled();
});

it("deletes exactly once with the explicit confirmation payload", async () => {
  const user = userEvent.setup(); mock.api.mockResolvedValue(undefined);
  const onDeleted = mount();
  await user.click(screen.getByRole("button", { name: "Delete account and data" }));
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "Confirm deletion" }));
  await waitFor(() => expect(onDeleted).toHaveBeenCalledTimes(1));
  expect(mock.api).toHaveBeenCalledExactlyOnceWith("/me", { method: "DELETE", body: '{"confirm":true}' });
});

it("shows an error while preserving confirmation when deletion fails", async () => {
  const user = userEvent.setup(); mock.api.mockRejectedValue(new Error("offline")); mount();
  await user.click(screen.getByRole("button", { name: "Delete account and data" }));
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "Confirm deletion" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect((screen.getByRole("checkbox") as HTMLInputElement).checked).toBe(true);
});

it("has named controls and no detectable axe violations", async () => {
  mount(); document.documentElement.lang = "en";
  const results = await axe.run(document.body, { rules: { "color-contrast": { enabled: false } } });
  expect(results.violations.map(issue => issue.id)).toEqual([]);
});
