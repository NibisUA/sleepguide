import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Home } from "../features/dashboard/Home";
import { History } from "../features/history/History";
import { useMe, useUpdateMe } from "../features/profile/api";
import { Settings } from "../features/settings/Settings";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } },
});

const TABS = ["home", "history", "settings"] as const;
type Tab = (typeof TABS)[number];

function Shell() {
  const { t, i18n } = useTranslation();
  const [tab, setTab] = useState<Tab>("home");
  const me = useMe();
  const updateMe = useUpdateMe();
  const bootstrapped = useRef(false);

  // Once per launch: apply the saved language and keep the stored time zone equal to the
  // device's (local dates of sleep sessions and "today" are computed in that zone).
  useEffect(() => {
    const user = me.data;
    if (!user || bootstrapped.current) return;
    bootstrapped.current = true;
    if (user.language !== i18n.language) void i18n.changeLanguage(user.language);
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zone && zone !== user.timezone) updateMe.mutate({ timezone: zone });
  }, [me.data, i18n, updateMe]);

  return (
    <>
      <div className="pb-20">
        {tab === "home" ? <Home /> : tab === "history" ? <History /> : <Settings />}
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-muted/20 bg-surface/95 backdrop-blur">
        <div
          className="mx-auto flex max-w-md"
          style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
        >
          {TABS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setTab(value)}
              className={`flex-1 py-3 text-sm ${
                tab === value ? "font-semibold text-primary" : "text-muted"
              }`}
            >
              {t(`nav.${value}`)}
            </button>
          ))}
        </div>
      </nav>
    </>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Shell />
    </QueryClientProvider>
  );
}
