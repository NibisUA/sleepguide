import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { PlanForm } from "./PlanForm";
import { Study } from "./Study";
import { itemsText, stats, textItems, type Plan } from "./api";

const mock = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../../lib/api", async original => ({ ...await original<typeof import("../../lib/api")>(), api: mock.api }));
const day = new Date().toLocaleDateString("en-CA");
const future = new Date(Date.now()+7*86400000).toISOString().slice(0, 10);
const plan: Plan = { id: 1, name: "Власна ціль", start_date: day, deadline: future, reserve_days: 1, daily_capacity: null, version: 1, created_at: new Date().toISOString(), items: [{ label: "1", title: "", group: "", weight: 1, scheduled_date: day, done_at: null }, { label: "2", title: "", group: "", weight: 2, scheduled_date: day, done_at: null }] };
function mount(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{node}</QueryClientProvider>);
}
beforeEach(() => {
  mock.api.mockReset(); mock.api.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === "/me") return { timezone: "Europe/Kyiv" };
    if (path === "/study/plans" && !init?.method) return [plan];
    if (path.includes("replan-preview")) return { expected_version: 1, assignments: { "1": future, "2": future }, summary: { status: "active" } };
    if (path === "/study/preview" || path.startsWith("/study/preview?")) {
      const body = JSON.parse(String(init?.body));
      return { items: body.items ?? plan.items, working_days: 6 };
    }
    return plan;
  });
});

it("requires just name deadline and total to preview and save a simple plan", async () => {
  const close = vi.fn(), user = userEvent.setup(); mount(<PlanForm onClose={close} />);
  await user.type(screen.getByLabelText("Назва предмета або цілі"), "Моя ціль");
  fireEvent.change(screen.getByLabelText("Дедлайн"), { target: { value: future } });
  await user.type(screen.getByLabelText("Кількість питань"), "2");
  await user.click(screen.getByRole("button", { name: "Переглянути план" }));
  expect(await screen.findByRole("button", { name: "Зберегти план" })).toBeTruthy();
  expect(mock.api.mock.calls.filter(([path, init]) => path === "/study/plans" && init?.method)).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "Зберегти план" }));
  await waitFor(() => expect(close).toHaveBeenCalled());
  const call = mock.api.mock.calls.find(([path, init]) => path === "/study/plans" && init?.method);
  expect(JSON.parse(call![1].body)).toMatchObject({ name: "Моя ціль", reserve_days: 0, preserve_schedule: true, total: 2 });
});

it("imports text with an explicitly selected year and keeps scheduled dates", async () => {
  mock.api.mockImplementation(async (path: string, init?: RequestInit) => path === "/study/parse" ? { name: "Моя ціль", deadline: future, start_date: day, total: 2, declared_total: null, reserve_days: 0, reserve_dates: [], preserve_schedule: true, issues: [], items: plan.items } : { items: plan.items, working_days: 6 });
  const user = userEvent.setup(); mount(<PlanForm onClose={vi.fn()} />);
  await user.click(screen.getByRole("button", { name: "Із тексту" }));
  await user.type(screen.getByLabelText("Текст для розпізнавання"), "25 жовтня — питання 1–2");
  await user.type(screen.getByLabelText("Рік для дат без року (за потреби)"), "2026");
  await user.click(screen.getByRole("button", { name: "Розпізнати структуру" }));
  await screen.findByText(/Знайдено готовий розклад/);
  expect(mock.api).toHaveBeenCalledWith("/study/parse", { method: "POST", body: JSON.stringify({ text: "25 жовтня — питання 1–2", year: 2026 }) });
  await user.click(screen.getByRole("button", { name: "Переглянути план" }));
  await screen.findByRole("button", { name: "Зберегти план" });
  const body = JSON.parse(mock.api.mock.calls.find(([path]) => path === "/study/preview")![1].body);
  expect(body.preserve_schedule).toBe(true); expect(body.items[0].scheduled_date).toBe(day);
});

it("requires review of ambiguous import data", async () => {
  mock.api.mockResolvedValue({ name: "Моя ціль", deadline: future, start_date: day, total: 2, declared_total: null, reserve_days: 0, reserve_dates: [], preserve_schedule: false, items: plan.items, issues: [{ line: 1, message: "Пропуск номера" }] });
  const user = userEvent.setup(); mount(<PlanForm onClose={vi.fn()} />);
  await user.click(screen.getByRole("button", { name: "Із тексту" }));
  await user.type(screen.getByLabelText("Текст для розпізнавання"), "1, 3");
  await user.click(screen.getByRole("button", { name: "Розпізнати структуру" }));
  await screen.findByText(/Пропуск номера/);
  await user.click(screen.getByRole("button", { name: "Переглянути план" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Перевір позначені");
});

it("edits a numbered plan without discarding its existing version", async () => {
  const user = userEvent.setup(); mount(<PlanForm plan={plan} onClose={vi.fn()} />);
  await user.clear(screen.getByLabelText("Назва предмета або цілі")); await user.type(screen.getByLabelText("Назва предмета або цілі"), "Оновлена ціль");
  await user.click(screen.getByRole("button", { name: "Переглянути план" }));
  await screen.findByRole("button", { name: "Зберегти план" });
  const call = mock.api.mock.calls.find(([path]) => path.startsWith("/study/preview?"));
  expect(JSON.parse(call![1].body).expected_version).toBe(1);
});

it("resizes a simple numbered plan while retaining existing item metadata", async () => {
  const user = userEvent.setup(); mount(<PlanForm plan={plan} onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Кількість питань"), { target: { value: "3" } });
  await user.click(screen.getByRole("button", { name: "Переглянути план" }));
  await screen.findByRole("button", { name: "Зберегти план" });
  const body = JSON.parse(mock.api.mock.calls.find(([path]) => path.startsWith("/study/preview?"))![1].body);
  expect(body.items.map((row: { label: string }) => row.label)).toEqual(["1", "2", "3"]);
  expect(body.items[1].weight).toBe(2); expect(body.preserve_schedule).toBe(false);
});

it("shows a combined today list and persists a checkbox through the API", async () => {
  mount(<Study />); const user = userEvent.setup();
  const todaySection = (await screen.findByText(/Сьогодні ·/)).closest("section")!;
  const checkbox = await within(todaySection).findByRole("checkbox", { name: "Власна ціль: питання 1" });
  await user.click(checkbox);
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith("/study/plans/1/items/1", { method: "POST", body: JSON.stringify({ expected_version: 1, done: true }) }));
});

it("replans only after showing a preview and explicit confirmation", async () => {
  mount(<Study />); const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Перепланувати невиконане" }));
  const dialog = screen.getByRole("dialog");
  await within(dialog).findByLabelText("Нова дата 1");
  expect(mock.api.mock.calls.some(([path]) => path.endsWith("/schedule"))).toBe(false);
  fireEvent.change(within(dialog).getByLabelText("Нова дата 1"), { target: { value: day } });
  await user.click(within(dialog).getByRole("button", { name: "Підтвердити новий розклад" }));
  await waitFor(() => expect(mock.api.mock.calls.some(([path]) => path.endsWith("/schedule"))).toBe(true));
  expect(JSON.parse(mock.api.mock.calls.find(([path]) => path.endsWith("/schedule"))![1].body).assignments["1"]).toBe(day);
});

it("detects duplicate or malformed custom rows and preserves prefixed labels", () => {
  expect(textItems(itemsText([{ ...plan.items[0], label: "N1.8" }]))[0].label).toBe("N1.8");
  expect(() => textItems("1.2 | | 1")).toThrow();
  expect(() => textItems("1 | 2026-02-31 | 1")).toThrow();
});

it("distinguishes expired and overloaded plans without a division by zero", () => {
  expect(stats({ ...plan, deadline: "2020-01-01" }, day)).toMatchObject({ status: "Дедлайн минув", daily: null });
  expect(stats({ ...plan, daily_capacity: 1, items: [{ ...plan.items[0], weight: 100 }] }, day).status).toContain("ліміт");
});
