import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal } from "../../components/Modal";
import { DataTransferSection } from "../transfer/DataTransferSection";

import { DurationBars, ScoreLine } from "../../components/charts";
import { confirmAction } from "../../lib/confirm";
import { formatDate, formatDuration, formatTime, isoDate } from "../../lib/format";
import { scoreColor } from "../../lib/score";
import type { SleepSession } from "../../types/api";
import { useMe } from "../profile/api";
import {
  useCreateSleep,
  useDeleteSleep,
  useSleepHistory,
  useSleepList,
  useUpdateSleep,
} from "../sleep/api";
import { SleepForm, dayDefaults, type SleepFormValues } from "../sleep/SleepForm";
import { ScreenTimeHistory } from "../screentime/ScreenTimeHistory";
import { StressHistory } from "../stress/StressHistory";
import { DaySummarySheet } from "../day/DaySummarySheet";
import { WorkoutHistory } from "../workout/WorkoutHistory";
import { RecordsSection } from "../records/RecordsSection";
import { YearHeatmap } from "./YearHeatmap";
import { sleepPoints, useHistoryEntries, useHistoryOverview, type HistoryRange } from "./api";
import { BucketNote, ChartScroll, EntryPager, PeriodCaption, RangePicker } from "./HistoryControls";

export function History() {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const today = isoDate(new Date());

  const [range, setRange] = useState<HistoryRange>("7d");
  const [year, setYear] = useState(() => new Date().getFullYear());
  const [selected, setSelected] = useState<string>(today);
  const [editing, setEditing] = useState<SleepSession | null>(null);
  const [creating, setCreating] = useState(false);
  const [summaryDate, setSummaryDate] = useState<string | null>(null);
  const [transferOpen, setTransferOpen] = useState(false);

  const me = useMe();
  const overview = useHistoryOverview(range);
  const yearDays = useSleepHistory(`${year}-01-01`, `${year}-12-31`);
  const daySessions = useSleepList(50, selected);
  const recent = useHistoryEntries("sleep", overview.data?.from_date, overview.data?.to_date);

  const create = useCreateSleep();
  const update = useUpdateSleep();
  const remove = useDeleteSleep();
  const busy = create.isPending || update.isPending;
  const writeError = editing ? update.error : create.error;

  const days = overview.data ? sleepPoints(overview.data) : [];
  const averageScore = overview.data?.sleep.average_score == null ? null : Math.round(overview.data.sleep.average_score);
  const averageDuration = overview.data?.sleep.average_minutes == null ? null : Math.round(overview.data.sleep.average_minutes);
  const selectedDay = (yearDays.data ?? []).find(day => day.date === selected) ?? null;
  const recentRows = recent.data?.pages.flatMap(page => page.sleep_sessions) ?? [];

  function closeForm() {
    setEditing(null);
    setCreating(false);
  }

  function save(values: SleepFormValues) {
    if (editing) {
      update.mutate({ id: editing.id, ...values }, { onSuccess: closeForm });
    } else {
      create.mutate(values, { onSuccess: closeForm });
    }
  }

  async function deleteSession(session: SleepSession) {
    if (await confirmAction(t("sleep.deleteConfirm"))) {
      remove.mutate(session.id, { onSuccess: closeForm });
    }
  }

  function startEditing(session: SleepSession) {
    setCreating(false);
    setEditing(session);
    if (session.local_date) { setSelected(session.local_date); setYear(Number(session.local_date.slice(0, 4))); }
  }

  return (
    <main className="mx-auto max-w-md space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("history.title")}</h1>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setCreating(true);
          }}
          className="rounded-full bg-primary px-3 py-1.5 text-sm font-medium text-on-primary"
        >
          {t("sleep.add")}
        </button>
      </div>

      <button type="button" onClick={() => setTransferOpen(true)} className="min-h-11 text-sm text-primary">{t("transfer.title")}</button>
      {transferOpen && <Modal title={t("transfer.title")} onClose={() => setTransferOpen(false)}>
        <DataTransferSection onImported={() => setRange("all")} />
        <button type="button" onClick={() => setTransferOpen(false)} className="mt-3 min-h-11 w-full text-primary">{t("day.close")}</button>
      </Modal>}

      {(creating || editing) && (
        <section className="rounded-3xl bg-surface p-5">
          <SleepForm
            key={editing ? editing.id : "new"}
            title={editing ? t("sleep.formEditTitle") : t("sleep.formTitle")}
            initial={
              editing
                ? { started_at: editing.started_at, ended_at: editing.ended_at ?? editing.started_at }
                : dayDefaults(selected)
            }
            busy={busy}
            error={writeError}
            onSubmit={save}
            onCancel={closeForm}
          />
        </section>
      )}

      <section className="rounded-3xl bg-surface p-5">
        <RangePicker value={range} onChange={setRange} />
        {overview.data && <PeriodCaption overview={overview.data} />}

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-2xl bg-bg p-3">
            <p className="text-xs text-muted">{t("history.avgScore")}</p>
            <p
              className={`mt-1 text-2xl font-semibold ${
                averageScore !== null ? scoreColor(averageScore) : "text-muted"
              }`}
            >
              {averageScore ?? "—"}
            </p>
          </div>
          <div className="rounded-2xl bg-bg p-3">
            <p className="text-xs text-muted">{t("history.avgDuration")}</p>
            <p className="mt-1 text-2xl font-semibold">
              {averageDuration !== null ? formatDuration(t, averageDuration) : "—"}
            </p>
          </div>
        </div>

        {overview.isPending ? <Skeleton /> : overview.isError ?
          <QueryError error={overview.error} retry={() => void overview.refetch()} /> : <>
          <p className="mt-5 text-sm text-muted">{t("history.durationChart")}</p>
          <BucketNote overview={overview.data} kind="sleep" />
          <ChartScroll count={days.length}><DurationBars days={days} goal={me.data?.sleep_goal_minutes ?? 480} locale={locale} /></ChartScroll>
          <p className="mt-5 text-sm text-muted">{t("history.scoreChart")}</p>
          <ChartScroll count={days.length}><ScoreLine days={days} locale={locale} /></ChartScroll>
        </>}
      </section>

      {overview.data && <WorkoutHistory key={"workout-" + range} overview={overview.data} />}
      <RecordsSection />

      {overview.data && <StressHistory key={"stress-" + range} overview={overview.data} />}

      {overview.data && <ScreenTimeHistory key={"screen-" + range} overview={overview.data} />}

      <section className="rounded-3xl bg-surface p-5">
        <div className="flex items-center justify-between">
          <p className="font-medium">{t("history.heatmap")}</p>
          <div className="flex items-center gap-3 text-sm">
            <button
              type="button"
              onClick={() => setYear(year - 1)}
              aria-label={t("history.prevYear")}
              className="text-muted"
            >
              ‹
            </button>
            <span className="tabular-nums">{year}</span>
            <button
              type="button"
              onClick={() => setYear(year + 1)}
              disabled={year >= new Date().getFullYear()}
              aria-label={t("history.nextYear")}
              className="text-muted"
            >
              ›
            </button>
          </div>
        </div>
        <div className="mt-3">
          {yearDays.isPending ? <Skeleton /> : yearDays.isError ? <QueryError error={yearDays.error} retry={() => void yearDays.refetch()} /> : <YearHeatmap
            year={year}
            days={yearDays.data ?? []}
            selected={selected}
            onSelect={(date) => {
              setSelected(date);
              closeForm();
            }}
          />}
        </div>
      </section>

      <section className="rounded-3xl bg-surface p-5">
        <div className="flex items-center justify-between">
          <p className="font-medium">
            {formatDate(selected, locale, { day: "numeric", month: "long", year: "numeric" })}
          </p>
          {selectedDay?.score != null && (
            <span className={`text-2xl font-semibold ${scoreColor(selectedDay.score)}`}>
              {selectedDay.score}
            </span>
          )}
        </div>
        <label className="mt-3 block text-sm text-muted">
          {t("history.selectDate")}
          <input type="date" value={selected} max={today}
            onChange={(event) => { if (event.target.value) { setSelected(event.target.value); setYear(Number(event.target.value.slice(0, 4))); } }}
            className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text" />
        </label>
        {selectedDay && selectedDay.sleep_minutes > 0 ? (
          <p className="mt-1 text-sm text-muted">
            {formatDuration(t, selectedDay.sleep_minutes)}
            {selectedDay.bedtime && selectedDay.wake_time
              ? ` · ${formatTime(selectedDay.bedtime, locale)} → ${formatTime(selectedDay.wake_time, locale)}`
              : ""}
            {selectedDay.nap_minutes > 0
              ? ` · ${t("sleep.nap")} ${formatDuration(t, selectedDay.nap_minutes)}`
              : ""}
          </p>
        ) : (
          <p className="mt-1 text-sm text-muted">{t("history.noSleep")}</p>
        )}

        <button
          type="button"
          onClick={() => setSummaryDate(selected)}
          className="mt-3 w-full rounded-2xl border border-primary/50 py-2.5 text-sm font-medium text-primary"
        >
          {t("day.summaryButton")}
        </button>

        {daySessions.isPending && <Skeleton />}
        {daySessions.isError && <QueryError error={daySessions.error} retry={() => void daySessions.refetch()} />}
        {remove.isError && <p role="alert" className="text-danger">{t("common.error")}</p>}
        <ul className="mt-2 divide-y divide-muted/10">
          {daySessions.data?.map((session) => (
            <SessionRow
              key={session.id}
              session={session}
              locale={locale}
              onEdit={() => startEditing(session)}
              onDelete={() => void deleteSession(session)}
            />
          ))}
        </ul>

        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setCreating(true);
          }}
          className="mt-2 text-sm text-primary"
        >
          {t("history.addForDay")}
        </button>
      </section>

      <section className="rounded-3xl bg-surface p-5">
        <p className="font-medium">{t("history.entries")}</p>
        {recent.isPending && <Skeleton />}
        {recent.isError && !recent.data && <QueryError error={recent.error} retry={() => void recent.refetch()} />}
        {recent.isSuccess && recentRows.length === 0 && <p className="mt-2 text-sm text-muted">{t("history.noSleep")}</p>}
        <ul className="mt-2 divide-y divide-muted/10">
          {recentRows.map((session) => (
              <SessionRow
                key={session.id}
                session={session}
                locale={locale}
                onEdit={() => startEditing(session)}
                onDelete={() => void deleteSession(session)}
              />
            ))}
        </ul>
        <EntryPager kind="sleep" query={recent} />
      </section>
      {summaryDate && <DaySummarySheet date={summaryDate} onClose={() => setSummaryDate(null)} />}
    </main>
  );
}

function SessionRow({
  session,
  locale,
  onEdit,
  onDelete,
}: {
  session: SleepSession;
  locale: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <li className="flex items-center justify-between gap-2 py-3">
      <div className="min-w-0">
        <p className="text-sm">
          {session.local_date
            ? formatDate(session.local_date, locale, { day: "numeric", month: "short", year: "numeric" })
            : "—"}{" "}
          <span className="text-muted">{formatDuration(t, session.duration_minutes ?? 0)}</span>
          {session.is_nap && <span className="ml-1 text-xs text-muted">· {t("sleep.nap")}</span>}
        </p>
        <p className="text-xs text-muted">
          {session.ended_at
            ? `${formatTime(session.started_at, locale)} → ${formatTime(session.ended_at, locale)}`
            : t("sleep.sleeping")}
        </p>
      </div>
      <div className="flex shrink-0 gap-3 text-sm">
        <button type="button" onClick={onEdit} className="text-primary">
          {t("sleep.edit")}
        </button>
        <button type="button" onClick={onDelete} className="text-danger">
          {t("sleep.delete")}
        </button>
      </div>
    </li>
  );
}
