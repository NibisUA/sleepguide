import { useEffect, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { QueryError } from "../../components/QueryState";
import { formatDate } from "../../lib/format";
import type { HistoryOverview } from "../../types/api";
import type { HistoryKind, HistoryRange } from "./api";

export function RangePicker({ value, onChange }: { value: HistoryRange; onChange: (range: HistoryRange) => void }) {
  const { t } = useTranslation();
  return <div role="group" aria-label={t("history.period")} className="grid grid-cols-2 gap-2">
    {(["7d", "30d", "90d", "all"] as const).map(range => <button key={range} type="button"
      aria-pressed={value === range} onClick={() => onChange(range)}
      className={"min-h-11 rounded-full px-2 py-2 text-sm " + (value === range ? "bg-primary font-semibold text-on-primary" : "border border-muted/30 text-muted")}>
      {t(`history.ranges.${range}`)}
    </button>)}
  </div>;
}

export function PeriodCaption({ overview }: { overview: HistoryOverview }) {
  const { t, i18n } = useTranslation();
  const options = { day: "numeric", month: "short", year: "numeric" } as const;
  return <div role="status" className="mt-3 space-y-1 text-xs text-muted">
    <p>{formatDate(overview.from_date, i18n.language, options)} — {formatDate(overview.to_date, i18n.language, options)}</p>
    <p>{t(overview.bucket_days === 1 ? "history.dailyPoints" : "history.groupedPoints", { n: overview.bucket_days })}</p>
    {!overview.has_data && <p>{t("history.emptyPeriod")}</p>}
  </div>;
}

export function ChartScroll({ count, children }: { count: number; children: ReactNode }) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { if (ref.current) ref.current.scrollLeft = ref.current.scrollWidth; }, [count]);
  return <div ref={ref} className="mt-2 overflow-x-auto" role="region" tabIndex={count > 30 ? 0 : undefined}
    aria-label={t("history.chartRegion")}>
    <div style={count > 30 ? { minWidth: count * 8 } : undefined}>{children}</div>
  </div>;
}

export function BucketNote({ overview, kind }: { overview: HistoryOverview; kind: HistoryKind }) {
  const { t } = useTranslation();
  if (overview.bucket_days === 1) return null;
  return <p className="mt-1 text-xs text-muted">{t(`history.bucketNotes.${kind}`, { n: overview.bucket_days })}</p>;
}

export function EntryPager({ kind, query }: { kind: HistoryKind; query: {
  hasNextPage: boolean; isFetchingNextPage: boolean; isFetchNextPageError: boolean;
  error: unknown; fetchNextPage: () => Promise<unknown>;
} }) {
  const { t } = useTranslation();
  return <>
    {query.isFetchNextPageError && <QueryError error={query.error} retry={() => void query.fetchNextPage()} />}
    {query.hasNextPage && <button type="button" disabled={query.isFetchingNextPage}
      onClick={() => void query.fetchNextPage()} className="mt-3 min-h-11 w-full rounded-2xl border border-primary/40 px-3 py-2 text-sm text-primary disabled:opacity-60">
      {query.isFetchingNextPage ? t("common.loading") : t("history.moreCategory", { category: t(`history.categories.${kind}`) })}
    </button>}
  </>;
}
