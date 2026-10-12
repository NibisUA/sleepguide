import { afterEach, expect, it, vi } from "vitest";
import { confirmAction } from "./confirm";
afterEach(() => { delete window.Telegram; vi.restoreAllMocks(); });
function host(initData: string, supported: boolean, showConfirm = vi.fn()) {
  window.Telegram = {WebApp: {initData, ready:vi.fn(), expand:vi.fn(), isVersionAtLeast:() => supported, showConfirm}};
  return showConfirm;
}
it("uses browser confirmation without the SDK", async () => {
  const fallback=vi.spyOn(window,"confirm").mockReturnValue(true);
  expect(await confirmAction("Delete?")).toBe(true); expect(fallback).toHaveBeenCalledWith("Delete?");
});
it("uses browser confirmation when the SDK has no Telegram host", async () => {
  const native=host("",true);
  vi.spyOn(window,"confirm").mockReturnValue(false);
  expect(await confirmAction("Delete?")).toBe(false); expect(native).not.toHaveBeenCalled();
});
it("does not call an unsupported native method", async () => {
  const native=host("signed",false);
  vi.spyOn(window,"confirm").mockReturnValue(false);
  expect(await confirmAction("Delete?")).toBe(false); expect(native).not.toHaveBeenCalled();
});
it("preserves confirmation in a supported Telegram host", async () => {
  host("signed",true,vi.fn((_message:string,callback:(b:boolean)=>void) => callback(true)));
  const fallback=vi.spyOn(window,"confirm");
  expect(await confirmAction("Delete?")).toBe(true); expect(fallback).not.toHaveBeenCalled();
});
it("falls back if a native method throws", async () => {
  host("signed",true,vi.fn(() => { throw Error("unsupported"); }));
  vi.spyOn(window,"confirm").mockReturnValue(false);
  expect(await confirmAction("Delete?")).toBe(false);
});
it("does not approve when browser confirmation also fails", async () => {
  vi.spyOn(window,"confirm").mockImplementation(() => { throw Error("blocked"); });
  expect(await confirmAction("Delete?")).toBe(false);
});
