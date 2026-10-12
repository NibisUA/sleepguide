import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Fragment, lazy, Suspense, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { QueryError, Skeleton } from "../components/QueryState";
import { ErrorBoundary } from "../components/ErrorBoundary";

import { Home } from "../features/dashboard/Home";
import { DAYS_KEY } from "../features/day/api";
import { INSIGHTS_KEY } from "../features/insights/api";
import { useMe, useUpdateMe } from "../features/profile/api";
import { QuickAddSheet } from "../features/quickadd/QuickAddSheet";
import { focusCard, type QuickTarget } from "../lib/focusCard";
import { isSessionClosed, resumeSession } from "../lib/api";
const History = lazy(() => import("../features/history/History").then(module => ({ default: module.History })));
const Insights = lazy(() => import("../features/insights/Insights").then(module => ({ default: module.Insights })));
const Settings = lazy(() => import("../features/settings/Settings").then(module => ({ default: module.Settings })));
const PrivacyPage = lazy(() => import("../features/privacy/PrivacyPage").then(module => ({ default: module.PrivacyPage })));

// Any successful write can change a day's summary, so those queries are refreshed after every
// mutation (the modules invalidate their own keys; this covers the aggregated one).
const queryClient: QueryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true, staleTime: 30_000 } },
  mutationCache: new MutationCache({
    onSuccess: (_data, _variables, _context, mutation) => {
      if (mutation.options.mutationKey?.[0] === "account") return;
      void queryClient.invalidateQueries({ queryKey: ["history"] });
      void queryClient.invalidateQueries({ queryKey: ["personal"] });
      void queryClient.invalidateQueries({ queryKey: ["progress"] });
      void queryClient.invalidateQueries({ queryKey: ["records"] });
      void queryClient.invalidateQueries({ queryKey: ["exercise-logs"] });
      void queryClient.invalidateQueries({ queryKey: DAYS_KEY });
      void queryClient.invalidateQueries({ queryKey: INSIGHTS_KEY });
    },
  }),
});

const TABS = ["home", "history", "insights", "settings"] as const;
type Tab = (typeof TABS)[number];

function Shell() {
  const { t, i18n } = useTranslation();
  const [tab, setTab] = useState<Tab>("home");
  const [quickOpen, setQuickOpen] = useState(false);
  const [deleted, setDeleted] = useState(isSessionClosed);
  const me = useMe(!deleted);
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

  function pickQuick(target: QuickTarget) {
    setQuickOpen(false);
    setTab("home");
    // Home may have just been mounted: wait for it before scrolling to the card.
    window.setTimeout(() => focusCard(target), 80);
  }

  useEffect(() => { document.documentElement.lang = i18n.language; }, [i18n.language]);
  useEffect(() => { window.scrollTo({ top: 0, left: 0, behavior: "auto" }); }, [tab]);
  if (deleted) return <main className="mx-auto max-w-md space-y-4 p-5">
    <h1 className="text-xl font-semibold">{t("privacy.deletedTitle")}</h1>
    <p className="text-muted">{t("privacy.deletedBody")}</p>
    <button type="button" className="w-full rounded-2xl border border-primary/50 py-3 text-primary"
      onClick={() => { resumeSession(); queryClient.clear(); bootstrapped.current = false; setTab("home"); setDeleted(false); }}>
      {t("privacy.restart")}
    </button>
  </main>;
  if (me.isPending) return <main className="mx-auto max-w-md space-y-4 p-4"><Skeleton /><Skeleton /></main>;
  if (me.isError) return <main className="mx-auto max-w-md p-4"><QueryError error={me.error} retry={() => void me.refetch()} /></main>;

  return (
    <>
      <div className="pb-24">
        <Suspense fallback={<main className="mx-auto max-w-md p-4"><Skeleton /></main>}>
        {tab === "home" ? (
          <Home />
        ) : tab === "history" ? (
          <History />
        ) : tab === "insights" ? (
          <Insights />
        ) : (
          <Settings onDeleted={() => setDeleted(true)} />
        )}
        </Suspense>
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-muted/20 bg-surface/95 backdrop-blur">
        <div
          className="mx-auto flex max-w-md items-center"
          style={{ paddingBottom: "max(env(safe-area-inset-bottom, 0px), var(--app-safe-bottom, 0px))" }}
        >
          {TABS.map((value, index) => (
            <Fragment key={value}>
              {index === 2 && (
                <button
                  type="button"
                  aria-label={t("quick.open")}
                  onClick={() => setQuickOpen(true)}
                  className="mx-1 -mt-4 h-12 w-12 shrink-0 rounded-full bg-primary text-3xl font-semibold leading-none text-on-primary shadow-lg transition active:scale-95"
                >
                  +
                </button>
              )}
              <button
                type="button"
                onClick={() => setTab(value)}
                aria-current={tab === value ? "page" : undefined}
                className={`flex-1 py-3 text-xs ${
                  tab === value ? "font-semibold text-primary" : "text-muted"
                }`}
              >
                {t(`nav.${value}`)}
              </button>
            </Fragment>
          ))}
        </div>
      </nav>
      {quickOpen && <QuickAddSheet onPick={pickQuick} onClose={() => setQuickOpen(false)} />}
    </>
  );
}

export function App() {
  const content = /^\/privacy(?:\/(uk|en))?\/?$/.test(window.location.pathname)
    ? <Suspense fallback={<Skeleton />}><PrivacyPage /></Suspense>
    : (
    <QueryClientProvider client={queryClient}>
      <Shell />
    </QueryClientProvider>
  );
  return <ErrorBoundary>{content}</ErrorBoundary>;
}
