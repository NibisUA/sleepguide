interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: { language_code?: string } };
  ready(): void;
  expand(): void;
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
}

export const getInitData = (): string => webApp()?.initData ?? "";
export const getTelegramLanguage = (): string | undefined =>
  webApp()?.initDataUnsafe?.user?.language_code;
