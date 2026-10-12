import { Modal } from "../../components/Modal";
import { QueryError, Skeleton } from "../../components/QueryState";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { addDays, formatDate, formatDuration, formatTime, isoDate } from "../../lib/format";
import { scoreColor } from "../../lib/score";
import { stressSoftClass, stressTextClass } from "../../lib/stress";
import type { DaySummary } from "../../types/api";
import { INTENSITY_COLOR, TYPE_ICON } from "../workout/meta";
import { useDaySummary } from "./api";
import { FeedbackCard } from "../personal/FeedbackCard";

function Section({ icon, title, children }: { icon: string; title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl bg-surface p-4">
      <h3 className="text-sm font-medium text-muted">
        {icon} {title}
      </h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

const Empty = ({ text }: { text: string }) => <p className="text-sm text-muted">{text}</p>;

function SleepPart({ summary }: { summary: DaySummary }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const score = summary.sleep_score;
  const sessions = [...summary.sleep_sessions].reverse(); // chronological
  if (!score && sessions.length === 0) return <Empty text={t("day.noSleep")} />;
  return (
    <>
      {score && (
        <p className="flex items-baseline gap-3">
          <span className={`text-4xl font-semibold ${scoreColor(score.score)}`}>{score.score}</span>
          <span className="text-sm text-muted">
            {formatDuration(t, score.sleep_minutes)}
            {score.limited_data ? ` · ${t("score.limited")}` : ""}
          </span>
        </p>
      )}
      <ul className="mt-2 space-y-1 text-sm">
        {sessions.map((session) => (
          <li key={session.id} className="flex justify-between gap-2">
            <span className="text-muted">
              {formatTime(session.started_at, locale)} → {session.ended_at ? formatTime(session.ended_at, locale) : ""}
              {session.is_nap ? ` · ${t("sleep.nap")}` : ""}
            </span>
            <span>{formatDuration(t, session.duration_minutes ?? 0)}</span>
          </li>
        ))}
      </ul>
      {score && summary.date >= addDays(isoDate(new Date()), -179) && <FeedbackCard key={summary.date} day={summary.date} />}
    </>
  );
}

function WorkoutPart({ summary }: { summary: DaySummary }) {
  const { t } = useTranslation();
  if (summary.workouts.length === 0) return <Empty text={t("day.noWorkouts")} />;
  return (
    <>
      <p className="text-sm">
        <span className="text-2xl font-semibold">{formatDuration(t, summary.workout_minutes)}</span>{" "}
        <span className="text-muted">· {t("day.workoutCount", { n: summary.workouts.length })}</span>
      </p>
      <ul className="mt-2 space-y-1 text-sm">
        {summary.workouts.map((workout) => (
          <li key={workout.id} className="flex justify-between gap-2">
            <span>
              {TYPE_ICON[workout.type]} {t(`workout.types.${workout.type}`)}
              <span className={`ml-1 text-xs ${INTENSITY_COLOR[workout.intensity]}`}>
                · {t(`workout.intensities.${workout.intensity}`)}
              </span>
            </span>
            <span className="text-muted">{formatDuration(t, workout.duration_minutes ?? 0)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

function StressPart({ summary }: { summary: DaySummary }) {
  const { t, i18n } = useTranslation();
  const { stress } = summary;
  if (stress.count === 0 || stress.average === null) return <Empty text={t("day.noStress")} />;
  return (
    <>
      <p className="text-sm">
        <span className={`text-2xl font-semibold ${stressTextClass(stress.average)}`}>
          {stress.average.toFixed(1)}
        </span>{" "}
        <span className="text-muted">
          · {t("day.stressPeak", { max: stress.max })} · {t("stress.count", { n: stress.count })}
        </span>
      </p>
      <ul className="mt-2 flex flex-wrap gap-2 text-sm">
        {[...summary.stress_logs].reverse().map((log) => (
          <li key={log.id} className={`rounded-lg px-2 py-1 ${stressSoftClass(log.level)}`}>
            {log.level}
            <span className="ml-1 text-xs opacity-80">
              {formatTime(log.logged_at, i18n.language)}
              {log.category ? ` · ${t(`stress.categories.${log.category}`)}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

function ScreenPart({ summary }: { summary: DaySummary }) {
  const { t } = useTranslation();
  const record = summary.screen_time;
  if (!record) return <Empty text={t("day.noScreen")} />;
  return (
    <p className="text-sm">
      <span className="text-2xl font-semibold">{formatDuration(t, record.total_minutes)}</span>
      {record.before_bed_minutes !== null && (
        <span className="text-muted">
          {" "}
          · {t("screen.beforeBedShort", { duration: formatDuration(t, record.before_bed_minutes) })}
        </span>
      )}
      {record.source === "shortcut" && <span className="text-muted"> · {t("screen.viaShortcut")}</span>}
    </p>
  );
}

/** Bottom sheet with the whole day: sleep, workouts, stress and screen time. */
export function DaySummarySheet({ date, onClose }: { date: string; onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const today = isoDate(new Date());
  const [day, setDay] = useState(date);
  const query = useDaySummary(day);

  const title = formatDate(day, locale, { weekday: "long", day: "numeric", month: "long" });

  return (
    <Modal title={title} onClose={onClose}>
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            aria-label={t("day.previous")}
            onClick={() => setDay(addDays(day, -1))}
            className="rounded-full px-3 py-1 text-xl text-muted"
          >
            ‹
          </button>
          <h2 className="text-center font-semibold capitalize">{title}</h2>
          <button
            type="button"
            aria-label={t("day.next")}
            disabled={day >= today}
            onClick={() => setDay(addDays(day, 1))}
            className="rounded-full px-3 py-1 text-xl text-muted disabled:opacity-30"
          >
            ›
          </button>
        </div>

        {query.isPending && <Skeleton />}
        {query.isError && <QueryError error={query.error} retry={() => void query.refetch()} />}
        {query.data && (
          <div className="mt-4 space-y-3">
            <Section icon="🌙" title={t("day.sleep")}>
              <SleepPart summary={query.data} />
            </Section>
            <Section icon="🏋️" title={t("day.workouts")}>
              <WorkoutPart summary={query.data} />
            </Section>
            <Section icon="🧠" title={t("day.stress")}>
              <StressPart summary={query.data} />
            </Section>
            <Section icon="📱" title={t("day.screen")}>
              <ScreenPart summary={query.data} />
            </Section>
          </div>
        )}

        <button
          type="button"
          onClick={onClose}
          className="mt-5 w-full rounded-2xl border border-muted/30 py-3 font-medium text-muted"
        >
          {t("day.close")}
        </button>
    </Modal>
  );
}
