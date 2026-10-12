import { afterEach, expect, it, vi } from "vitest";
import { initTelegram } from "./telegram";

afterEach(() => { delete window.Telegram; document.documentElement.removeAttribute("style"); });

it("updates safe areas when Telegram reports a content inset change", () => {
  const handlers = new Map<string, () => void>();
  const app = {
    initData: "test", ready: vi.fn(), expand: vi.fn(),
    safeAreaInset: { top: 20, bottom: 10 }, contentSafeAreaInset: { top: 4, bottom: 3 },
    onEvent: (event: string, callback: () => void) => { handlers.set(event, callback); },
  };
  window.Telegram = { WebApp: app };
  initTelegram();
  expect(document.documentElement.style.getPropertyValue("--app-safe-top")).toBe("24px");
  app.contentSafeAreaInset.bottom = 15;
  handlers.get("contentSafeAreaChanged")!();
  expect(document.documentElement.style.getPropertyValue("--app-safe-bottom")).toBe("25px");
  expect(app.ready).toHaveBeenCalledOnce();
});

it("keeps readable warning and error colors in Telegram's light theme", () => {
  window.Telegram = { WebApp: { initData: "test", ready: vi.fn(), expand: vi.fn(),
    themeParams: { bg_color: "#ffffff", text_color: "#111111", hint_color: "#eeeeee" },
  } };
  initTelegram();
  function luminance(hex: string) {
    const rgb = [1,3,5].map(index => parseInt(hex.slice(index,index+2),16)/255)
      .map(value => value <= 0.04045 ? value/12.92 : ((value+0.055)/1.055)**2.4);
    return rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722;
  }
  for (const variable of ["--color-muted","--color-warning","--color-danger"]) {
    const color = document.documentElement.style.getPropertyValue(variable);
    expect((1.05)/(luminance(color)+0.05)).toBeGreaterThanOrEqual(4.5);
  }
  expect(document.documentElement.style.colorScheme).toBe("light");
});
