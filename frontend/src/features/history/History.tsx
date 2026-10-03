import { useState } from "react";
import { useTranslation } from "react-i18next";

import { DurationBars, ScoreLine } from "../../components/charts";
import { addDays, formatDate, formatDuration, formatTime, isoDate } from "../../lib/format";
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
import { YearHeatmap } from "./YearHeatmap";

export function History() {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const today = isoDate(new Date());

  const [range, setRange] = useState<7 | 30>(7);
  const [year, setYear] = useState(() => new Date().getFullYear());
  const [selected, setSelected] = useState<string>(today);
  const [editing, setEditing] = useState<SleepSession | null>(null);
  const [creating, setCreating] = useState(false);

  const me = useMe();
  const rangeDays = useSleepHistory(addDays(today, -(range - 1)), today);
  const yearDays = useSleepHistory(`${year}-01-01`, `${year}-12-31`);
  const daySessions = useSleepList(50, selected);
  const recent = useSleepList(10);

  const create = useCreateSleep();
  const update = useUpdateSleep();
  const remove = useDeleteSleep();
  const busy = create.isPending || update.isPending;
  const writeError = editing ? update.error : create.error;

  const days = rangeDays.data ?? [];
  const scored = days.filter((day) => day.score !== null);
  const averageScore = scored.length
    ? Math.round(scored.reduce((sum, day) => sum + (day.score ?? 0), 0) / scored.length)
    : null;
  const slept = days.filter((day) => day.sleep_minutes > 0);
  const averageDuration = slept.length
    ? Math.round(slept.reduce((sum, day) => sum + day.sleep_minutes, 0) / slept.length)
    : null;
  const selectedDay =
    days.find((day) => day.date === selected) ??
    (yearDays.data ?? []).find((day) => day.date === selected) ??
    null;

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

  function deleteSession(session: SleepSession) {
    if (window.confirm(t("sleep.deleteConfirm"))) {
      remove.mutate(session.id, { onSuccess: closeForm });
    }
  }

  function startEditing(session: SleepSession) {
    setCreating(false);
    setEditing(session);
    if (session.local_date) setSelected(session.local_date);
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
          className="rounded-full bg-primary px-3 py-1.5 text-sm font-medium text-bg"
        >
          {t("sleep.add")}
        </button>
      </div>

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
        <div className="flex gap-2">
          {([7, 30] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setRange(value)}
              className={`flex-1 rounded-full py-2 text-sm ${
                range === value ? "bg-primary font-semibold text-bg" : "border border-muted/30 text-muted"
              }`}
            >
              {t(value === 7 ? "history.range7" : "history.range30")}
            </button>
          ))}
        </div>

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

        {rangeDays.isPending || rangeDays.isError ? (
          <p className="mt-5 text-sm text-muted">
            {rangeDays.isPending ? t("common.loading") : t("common.error")}
          </p>
        ) : (
          <>
            <p className="mt-5 text-sm text-muted">{t("history.durationChart")}</p>
            <DurationBars days={days} goal={me.data?.sleep_goal_minutes ?? 480} locale={locale} />
            <p className="mt-5 text-sm text-muted">{t("history.scoreChart")}</p>
            <ScoreLine days={days} locale={locale} />
          </>
        )}
      </section>

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
              aria-label={t("history.nextYear")}
              className="text-muted"
            >
              ›
            </button>
          </div>
        </div>
        <div className="mt-3">
          <YearHeatmap
            year={year}
            days={yearDays.data ?? []}
            selected={selected}
            onSelect={(date) => {
              setSelected(date);
              closeForm();
            }}
          />
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

        <ul className="mt-2 divide-y divide-muted/10">
          {daySessions.data?.map((session) => (
            <SessionRow
              key={session.id}
              session={session}
              locale={locale}
              onEdit={() => startEditing(session)}
              onDelete={() => deleteSession(session)}
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
        <p className="font-medium">{t("history.recent")}</p>
        <ul className="mt-2 divide-y divide-muted/10">
          {recent.data
            ?.filter((session) => session.ended_at !== null)
            .map((session) => (
              <SessionRow
                key={session.id}
                session={session}
                locale={locale}
                onEdit={() => startEditing(session)}
                onDelete={() => deleteSession(session)}
              />
            ))}
        </ul>
      </section>
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
            ? formatDate(session.local_date, locale, { day: "numeric", month: "short" })
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
