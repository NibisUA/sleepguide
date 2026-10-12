import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { StressBars } from "../../components/charts";
import { confirmAction } from "../../lib/confirm";
import { formatDate, formatTime } from "../../lib/format";
import { stressSoftClass, stressTextClass } from "../../lib/stress";
import type { HistoryOverview, StressLog } from "../../types/api";
import {
  useDeleteStress,
  useLogStress,
  useUpdateStress,
} from "./api";
import { StressForm, type StressFormValues } from "./StressForm";
import { stressPoints, useHistoryEntries } from "../history/api";
import { BucketNote, ChartScroll, EntryPager } from "../history/HistoryControls";

export function StressHistory({ overview }: { overview: HistoryOverview }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const list = useHistoryEntries("stress", overview.from_date, overview.to_date);
  const create = useLogStress();
  const update = useUpdateStress();
  const remove = useDeleteStress();

  const [editing, setEditing] = useState<StressLog | null>(null);
  const [creating, setCreating] = useState(false);

  const days = stressPoints(overview);
  const totalCount = overview.stress.count;
  const average = overview.stress.average;
  const peak = overview.stress.peak ?? 0;
  const entries = list.data?.pages.flatMap(page => page.stress_logs) ?? [];

  function closeForm() {
    setEditing(null);
    setCreating(false);
  }

  function save(values: StressFormValues) {
    if (editing) update.mutate({ id: editing.id, ...values }, { onSuccess: closeForm });
    else create.mutate(values, { onSuccess: closeForm });
  }

  async function deleteLog(log: StressLog) {
    if (await confirmAction(t("stress.deleteConfirm"))) {
      remove.mutate(log.id, { onSuccess: closeForm });
    }
  }

  if (list.isPending) return <Skeleton />;
  if (list.isError && !list.data) return <QueryError error={list.error} retry={() => void list.refetch()} />;

  return (
    <section className="rounded-3xl bg-surface p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">{t("stress.historyTitle")}</h2>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setCreating(true);
          }}
          className="rounded-full bg-primary px-3 py-1.5 text-sm font-medium text-on-primary"
        >
          {t("stress.add")}
        </button>
      </div>

      {(creating || editing) && (
        <StressForm
          key={editing ? editing.id : "new"}
          title={editing ? t("stress.formEditTitle") : t("stress.formTitle")}
          initial={
            editing
              ? { level: editing.level, category: editing.category, logged_at: editing.logged_at }
              : undefined
          }
          busy={create.isPending || update.isPending}
          error={editing ? update.error : create.error}
          onSubmit={save}
          onCancel={closeForm}
        />
      )}

      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("stress.avg")}</p>
          <p
            className={`mt-1 text-2xl font-semibold ${
              average !== null ? stressTextClass(average) : "text-muted"
            }`}
          >
            {average !== null ? average.toFixed(1) : "—"}
          </p>
        </div>
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("stress.peak")}</p>
          <p className={`mt-1 text-2xl font-semibold ${peak > 0 ? stressTextClass(peak) : "text-muted"}`}>
            {peak > 0 ? peak : "—"}
          </p>
        </div>
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("stress.records")}</p>
          <p className="mt-1 text-2xl font-semibold">{totalCount}</p>
        </div>
      </div>

      <>
          <p className="mt-5 text-sm text-muted">{t("stress.chartTitle")}</p>
          <BucketNote overview={overview} kind="stress" /><ChartScroll count={days.length}><StressBars days={days} locale={locale} /></ChartScroll>
        </>

      {entries.length === 0 && !list.isPending ? (
        <p className="mt-4 text-sm text-muted">{t("stress.noLogs")}</p>
      ) : (
        <ul className="mt-3 divide-y divide-muted/10">
          {entries.map((log) => (
            <li key={log.id} className="flex items-center justify-between gap-2 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-semibold ${stressSoftClass(log.level)}`}
                >
                  {log.level}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm">
                    {log.category ? t(`stress.categories.${log.category}`) : t("stress.noCategory")}
                  </p>
                  <p className="text-xs text-muted">
                    {formatDate(log.local_date, locale, { day: "numeric", month: "short", year: "numeric" })} · {formatTime(log.logged_at, locale)}
                  </p>
                </div>
              </div>
              <div className="flex shrink-0 gap-3 text-sm">
                <button
                  type="button"
                  onClick={() => {
                    setCreating(false);
                    setEditing(log);
                  }}
                  className="text-primary"
                >
                  {t("stress.edit")}
                </button>
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => void deleteLog(log)}
                  className="text-danger disabled:opacity-60"
                >
                  {t("stress.delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <EntryPager kind="stress" query={list} />
      {remove.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}</p>}
    </section>
  );
}
