import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ScreenTimeBars } from "../../components/charts";
import { confirmAction } from "../../lib/confirm";
import { addDays, formatDate, formatDuration } from "../../lib/format";
import { useDeleteScreenTime, usePutScreenTime } from "./api";
import type { HistoryOverview } from "../../types/api";
import { screenPoints, useHistoryEntries } from "../history/api";
import { BucketNote, ChartScroll, EntryPager } from "../history/HistoryControls";
import { ScreenTimeForm } from "./ScreenTimeForm";
import { CategoryBreakdown } from "./CategoryBreakdown";

export function ScreenTimeHistory({ overview }: { overview: HistoryOverview }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const today = overview.to_date;
  const query = useHistoryEntries("screen", overview.from_date, overview.to_date);
  const save = usePutScreenTime();
  const remove = useDeleteScreenTime();
  const [formDate, setFormDate] = useState<string | null>(null);

  const records = query.data?.pages.flatMap(page => page.screen_time) ?? [];
  const days = screenPoints(overview);
  const avgTotal = overview.screen.average_total == null ? null : Math.round(overview.screen.average_total);
  const avgBed = overview.screen.average_before_bed == null ? null : Math.round(overview.screen.average_before_bed);

  async function deleteRecord(date: string) {
    if (await confirmAction(t("screen.deleteConfirm"))) remove.mutate(date);
  }

  if (query.isPending) return <Skeleton />;
  if (query.isError && !query.data) return <QueryError error={query.error} retry={() => void query.refetch()} />;

  return (
    <section className="rounded-3xl bg-surface p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">{t("screen.historyTitle")}</h2>
        <button
          type="button"
          onClick={() => setFormDate(today)}
          className="rounded-full bg-primary px-3 py-1.5 text-sm font-medium text-on-primary"
        >
          {t("screen.add")}
        </button>
      </div>

      {formDate !== null && (
        <ScreenTimeForm
          key={formDate}
          title={t("screen.formTitle")}
          initialDate={formDate}
          records={records}
          busy={save.isPending}
          error={save.error}
          onSubmit={(values) => save.mutate(values, { onSuccess: () => setFormDate(null) })}
          onCancel={() => setFormDate(null)}
        />
      )}

      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("screen.avgTotal")}</p>
          <p className="mt-1 text-xl font-semibold">{avgTotal !== null ? formatDuration(t, avgTotal) : "—"}</p>
        </div>
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("screen.avgBed")}</p>
          <p className="mt-1 text-xl font-semibold">{avgBed !== null ? formatDuration(t, avgBed) : "—"}</p>
        </div>
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("screen.daysLogged")}</p>
          <p className="mt-1 text-xl font-semibold">
            {overview.screen.days}/{overview.days}
          </p>
        </div>
      </div>

      <>
          <p className="mt-5 text-sm text-muted">{t("screen.chartTitle")}</p>
          <BucketNote overview={overview} kind="screen" /><ChartScroll count={days.length}><ScreenTimeBars days={days} locale={locale} /></ChartScroll>
        </>

      {records.length === 0 && !query.isPending ? (
        <p className="mt-4 text-sm text-muted">{t("screen.noRecords")}</p>
      ) : (
        <ul className="mt-3 divide-y divide-muted/10">
          {records.map((record) => (
            <li key={record.local_date} className="flex items-center justify-between gap-2 py-3">
              <div className="min-w-0">
                <p className="text-sm">
                  <span className="font-semibold">{formatDuration(t, record.total_minutes)}</span>
                  {record.before_bed_minutes !== null && (
                    <span className="text-muted">
                      {" "}
                      · {t("screen.beforeBedShort", { duration: formatDuration(t, record.before_bed_minutes) })}
                    </span>
                  )}
                </p>
                <p className="text-xs text-muted">
                  {formatDate(record.local_date, locale, { day: "numeric", month: "short", year: "numeric" })}
                  {record.source === "shortcut" ? ` · ${t("screen.viaShortcut")}` : ""}
                </p>
                <CategoryBreakdown total={record.total_minutes} categories={record} compact />
              </div>
              <div className="flex shrink-0 gap-3 text-sm">
                <button type="button" disabled={record.local_date < addDays(today, -365)} title={record.local_date < addDays(today, -365) ? t("history.oldScreen") : undefined} onClick={() => setFormDate(record.local_date)} className="text-primary disabled:opacity-50">
                  {t("screen.edit")}
                </button>
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => void deleteRecord(record.local_date)}
                  className="text-danger disabled:opacity-60"
                >
                  {t("screen.delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <EntryPager kind="screen" query={query} />
      {remove.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}</p>}
    </section>
  );
}
