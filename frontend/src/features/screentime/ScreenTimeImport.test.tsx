import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { ScreenTimeForm } from "./ScreenTimeForm";
import type { ScreenTime } from "../../types/api";
import i18n from "../../lib/i18n";
import type { ScreenCategories } from "./categories";
const mock = vi.hoisted(() => ({data: [] as ScreenTime[], isPending:false, isError:false, categories: undefined as ScreenCategories | undefined}));
vi.mock("./api", () => ({useScreenTimeRange: () => ({...mock,refetch:vi.fn()})}));
vi.mock("./ScreenshotImport", () => ({ScreenshotImport: ({onPick}: {onPick:(m:number, categories?: ScreenCategories)=>void}) => <button onClick={() => onPick(265, mock.categories)}>OCR fixture choice</button>}));
beforeEach(async () => { await i18n.changeLanguage("uk"); mock.data=[]; mock.isPending=false; mock.isError=false; mock.categories=undefined; });
function setup(records: ScreenTime[] = []) {
  const save=vi.fn();
  render(<ScreenTimeForm title="Test" initialDate="2026-10-11" records={records} busy={false} error={null} onSubmit={save} onCancel={vi.fn()} />);
  return save;
}
async function pick() {
  await userEvent.click(screen.getByRole("button",{name:"Імпортувати скриншот"}));
  await userEvent.click(await screen.findByRole("button",{name:"OCR fixture choice"}));
}
it("prefills the chosen total but waits for an explicit save", async () => {
  const save=setup(); await pick(); expect(save).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button",{name:"Зберегти"}));
  expect(save).toHaveBeenCalledWith({date:"2026-10-11",total_minutes:265,before_bed_minutes:null});
});
it("prefills detected categories without saving until confirmation", async () => {
  mock.categories = { social_minutes: 120, entertainment_minutes: 60, games_minutes: 20 };
  const save=setup(); await pick(); expect(save).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button",{name:"Зберегти"}));
  expect(save).toHaveBeenCalledWith({date:"2026-10-11",total_minutes:265,before_bed_minutes:null,...mock.categories});
});
it("requires confirmation when the selected day already exists", async () => {
  const record={local_date:"2026-10-11",total_minutes:300,before_bed_minutes:null,source:"manual",updated_at:"2026-10-11T09:00:00Z"} as ScreenTime;
  const save=setup([record]); await pick();
  await userEvent.click(screen.getByRole("button",{name:"Зберегти"}));
  expect(save).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("checkbox",{name:/Підтверджую заміну/}));
  await userEvent.click(screen.getByRole("button",{name:"Зберегти"})); expect(save).toHaveBeenCalledOnce();
});
it("keeps OCR total when the user corrects the date", async () => {
  const save=setup(); await pick();
  await userEvent.clear(screen.getByLabelText("День"));
  await userEvent.type(screen.getByLabelText("День"),"2026-10-10");
  await waitFor(() => expect((screen.getByLabelText("День") as HTMLInputElement).value).toBe("2026-10-10"));
  await userEvent.click(screen.getByRole("button",{name:"Зберегти"}));
  expect(save).toHaveBeenCalledWith({date:"2026-10-10",total_minutes:265,before_bed_minutes:null});
});
it("blocks save while checking a previously unloaded date", async () => {
  setup(); await pick(); mock.isError=true;
  // Re-rendering the form observes a failed lookup, so it cannot overwrite an unknown record.
  await userEvent.clear(screen.getByLabelText("День"));
  await userEvent.type(screen.getByLabelText("День"),"2026-10-09");
  expect(screen.getByRole("button",{name:"Зберегти"}).hasAttribute("disabled")).toBe(true);
});
