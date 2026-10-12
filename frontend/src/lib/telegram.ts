interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: { language_code?: string } };
  ready(): void;
  expand(): void;
  showConfirm?(message: string, callback: (confirmed: boolean) => void): void;
  isVersionAtLeast?(version: string): boolean;
  themeParams?: {
    bg_color?: string; secondary_bg_color?: string; text_color?: string;
    hint_color?: string; button_color?: string; button_text_color?: string;
  };
  safeAreaInset?: { top: number; bottom: number };
  contentSafeAreaInset?: { top: number; bottom: number };
  onEvent?(event: string, callback: () => void): void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

const webApp = () => window.Telegram?.WebApp;

export function initTelegram(): void {
  webApp()?.ready();
  webApp()?.expand();
  const app = webApp();
  if (!app?.initData) return;
  function syncTheme() {
    const params = app?.themeParams;
    const colors = {
      bg: params?.bg_color, surface: params?.secondary_bg_color, text: params?.text_color,
      muted: params?.hint_color, primary: params?.button_color, "on-primary": params?.button_text_color,
    };
    for (const [key, value] of Object.entries(colors)) {
      if (value && /^#[\da-f]{6}$/i.test(value)) {
        document.documentElement.style.setProperty(`--color-${key}`, value);
      }
    }
    const background = params?.bg_color;
    if (background && /^#[\da-f]{6}$/i.test(background)) {
      const r = parseInt(background.slice(1, 3), 16), g = parseInt(background.slice(3, 5), 16), b = parseInt(background.slice(5, 7), 16);
      const light = 0.2126 * r + 0.7152 * g + 0.0722 * b > 140;
      // Use a readable secondary text tone even if the Telegram hint color is faint.
      document.documentElement.style.setProperty("--color-muted", light ? "#5f6b65" : "#94a69d");
      document.documentElement.style.colorScheme = light ? "light" : "dark";
      document.documentElement.style.setProperty("--color-danger", light ? "#b42318" : "#d94a4a");
      document.documentElement.style.setProperty("--color-warning", light ? "#8f6100" : "#e5a63a");
    }
    document.documentElement.lang = getTelegramLanguage()?.startsWith("uk") ? "uk" : "en";
  }
  function syncInsets() {
    for (const side of ["top", "bottom"] as const) {
      const value = Math.max(0, (app?.safeAreaInset?.[side] ?? 0) + (app?.contentSafeAreaInset?.[side] ?? 0));
      document.documentElement.style.setProperty(`--app-safe-${side}`, `${value}px`);
    }
  }
  syncTheme();
  syncInsets();
  app.onEvent?.("themeChanged", syncTheme);
  app.onEvent?.("safeAreaChanged", syncInsets);
  app.onEvent?.("contentSafeAreaChanged", syncInsets);
}

export const getInitData = (): string => webApp()?.initData ?? "";
export const getTelegramLanguage = (): string | undefined =>
  webApp()?.initDataUnsafe?.user?.language_code;
