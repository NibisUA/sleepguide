/** Native Telegram confirm dialog inside the Mini App, `window.confirm` elsewhere (browser dev). */
export function confirmAction(message: string): Promise<boolean> {
  const webApp = window.Telegram?.WebApp;
  return new Promise(resolve => {
    // Loading the SDK in a browser exposes methods even with no Telegram host.
    if (webApp?.initData && webApp.showConfirm && webApp.isVersionAtLeast?.("6.2")) {
      try { webApp.showConfirm(message, resolve); return; } catch { /* fall back */ }
    }
    try { resolve(window.confirm(message)); } catch { resolve(false); }
  });
}
