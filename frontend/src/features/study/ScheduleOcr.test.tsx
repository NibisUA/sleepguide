import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ScheduleOcr } from "./ScheduleOcr";

const mock = vi.hoisted(() => ({ recognize: vi.fn(), terminate: vi.fn(), setParameters: vi.fn() }));
vi.mock("tesseract.js", () => ({ createWorker: async () => mock, PSM: { AUTO: 3 } }));
beforeEach(() => {
  vi.restoreAllMocks(); mock.recognize.mockReset(); mock.terminate.mockReset(); mock.setParameters.mockReset();
  mock.terminate.mockResolvedValue(undefined); mock.setParameters.mockResolvedValue(undefined);
  Object.defineProperty(Image.prototype, "decode", { configurable: true, value: vi.fn().mockResolvedValue(undefined) });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ fillRect: vi.fn(), drawImage: vi.fn(), getImageData: () => ({ data: new Uint8ClampedArray(16).fill(255) }), putImageData: vi.fn() } as unknown as CanvasRenderingContext2D);
  URL.createObjectURL = vi.fn(() => "blob:local-ocr"); URL.revokeObjectURL = vi.fn();
});

it("reads multiple screenshots sequentially and combines actual recognized text", async () => {
  const picked = vi.fn(); mock.recognize.mockResolvedValueOnce({ data: { text: "25 жовтня — питання 1–9" } }).mockResolvedValueOnce({ data: { text: "26 жовтня — 10–16" } });
  render(<ScheduleOcr onText={picked} />);
  fireEvent.change(screen.getByLabelText("Скриншоти розкладу"), { target: { files: [new File(["x"], "one.png", { type: "image/png" }), new File(["y"], "two.png", { type: "image/png" })] } });
  await waitFor(() => expect(picked).toHaveBeenCalledWith("25 жовтня — питання 1–9\n\n26 жовтня — 10–16"));
  expect(mock.recognize).toHaveBeenCalledTimes(2);
  await waitFor(() => expect(mock.terminate).toHaveBeenCalledTimes(1));
  expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2);
});

it("shows OCR failures instead of generating a fake schedule", async () => {
  const picked = vi.fn(); mock.recognize.mockRejectedValue(new Error("Не вдалося прочитати зображення"));
  render(<ScheduleOcr onText={picked} />);
  fireEvent.change(screen.getByLabelText("Скриншоти розкладу"), { target: { files: [new File(["x"], "one.png", { type: "image/png" })] } });
  expect((await screen.findByRole("alert")).textContent).toContain("Не вдалося прочитати");
  expect(picked).not.toHaveBeenCalled();
  await waitFor(() => expect(mock.terminate).toHaveBeenCalled());
});

it("rejects excess files before starting OCR", () => {
  render(<ScheduleOcr onText={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Скриншоти розкладу"), { target: { files: Array.from({ length: 9 }, (_, i) => new File(["x"], `${i}.png`, { type: "image/png" })) } });
  expect(screen.getByRole("alert").textContent).toContain("до 8");
  expect(mock.recognize).not.toHaveBeenCalled();
});
