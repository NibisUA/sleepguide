import { useTranslation } from "react-i18next";

import { formatDate, formatDuration } from "../lib/format";
import { stressFillClass } from "../lib/stress";
import type { SleepDay, StressDay } from "../types/api";

function pointLabel(day: { date: string; end_date?: string }, locale: string) {
  const options = { day: "numeric", month: "short", year: "numeric" } as const;
  const start = formatDate(day.date, locale, options);
  return day.end_date && day.end_date !== day.date
    ? start + " – " + formatDate(day.end_date, locale, options) : start;
}

const WIDTH = 320;
const HEIGHT = 104;
const PAD = 8;

/** Nightly sleep duration as bars, with a dashed sleep-goal line. */
export function DurationBars({
  days,
  goal,
  locale,
}: {
  days: (Pick<SleepDay, "date" | "sleep_minutes"> & { end_date?: string })[];
  goal: number;
  locale: string;
}) {
  const { t } = useTranslation();
  if (days.length === 0) return null;

  const rawMax = Math.max(goal, ...days.map((day) => day.sleep_minutes), 60);
  const max = Math.ceil(rawMax / 60) * 60; // round up to the next full hour
  const slot = WIDTH / days.length;
  const barWidth = Math.max(slot * 0.62, 2);
  const y = (minutes: number) => HEIGHT - PAD - (Math.min(minutes, max) / max) * (HEIGHT - 2 * PAD);
  const goalY = y(goal);

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: HEIGHT }} preserveAspectRatio="none" role="img" aria-label={t("history.durationChart")}>
        {days.map((day, index) => {
          const x = index * slot + (slot - barWidth) / 2;
          const top = y(day.sleep_minutes);
          const ratio = Math.min(day.sleep_minutes / goal, 1);
          return (
            <rect
              key={day.date}
              x={x}
              y={day.sleep_minutes > 0 ? top : HEIGHT - PAD - 1}
              width={barWidth}
              height={day.sleep_minutes > 0 ? HEIGHT - PAD - top : 1}
              rx={2}
              className="fill-primary"
              opacity={day.sleep_minutes > 0 ? 0.25 + 0.75 * ratio : 0.08}
            >
              <title>{`${pointLabel(day, locale)} · ${formatDuration(t, day.sleep_minutes)}`}</title>
            </rect>
          );
        })}
        <line
          x1={PAD}
          x2={WIDTH - PAD}
          y1={goalY}
          y2={goalY}
          className="stroke-warning"
          strokeWidth={1}
          strokeDasharray="4 4"
        />
      </svg>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>{formatDate(days[0].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
        <span className="text-warning">{t("history.goal", { value: formatDuration(t, goal) })}</span>
        <span>{formatDate(days[days.length - 1].end_date ?? days[days.length - 1].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
      </div>
    </div>
  );
}

/** Sleep Score over time with the 70 / 85 band markers. */
export function ScoreLine({ days, locale }: { days: (Pick<SleepDay, "date" | "score"> & { end_date?: string })[]; locale: string }) {
  const { t } = useTranslation();
  const withScore = days.filter((day) => day.score !== null);
  if (withScore.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">{t("history.noScore")}</p>;
  }

  const step = days.length > 1 ? (WIDTH - 2 * PAD) / (days.length - 1) : 0;
  const x = (index: number) => PAD + index * step;
  const y = (score: number) => HEIGHT - PAD - (score / 100) * (HEIGHT - 2 * PAD);
  let drawing = false;
  const path = days.map((day, index) => {
    if (day.score === null) { drawing = false; return ""; }
    const command = drawing ? "L" : "M";
    drawing = true;
    return command + x(index) + "," + y(day.score);
  }).join(" ");


  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: HEIGHT }} preserveAspectRatio="none" role="img" aria-label={t("history.scoreChart")}>
        {[70, 85].map((band) => (
          <line
            key={band}
            x1={PAD}
            x2={WIDTH - PAD}
            y1={y(band)}
            y2={y(band)}
            className="stroke-muted/30"
            strokeWidth={1}
            strokeDasharray="2 4"
          />
        ))}
        <path d={path} fill="none" className="stroke-primary" strokeWidth={2} strokeLinejoin="round" />
        {days.map((day, index) =>
          day.score === null ? null : (
            <circle
              key={day.date}
              cx={x(index)}
              cy={y(day.score)}
              r={2.5}
              className="fill-primary"
            >
              <title>{`${pointLabel(day, locale)} · ${day.score}`}</title>
            </circle>
          ),
        )}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>0</span>
        <span>70 / 85</span>
        <span>100</span>
      </div>
    </div>
  );
}

/** Minutes of training per day as bars (days without training stay as faint stubs). */
export function MinutesBars({
  days,
  locale,
}: {
  days: { date: string; end_date?: string; minutes: number; count: number }[];
  locale: string;
}) {
  const { t } = useTranslation();
  if (days.length === 0) return null;

  const max = Math.max(Math.ceil(Math.max(...days.map((day) => day.minutes), 30) / 30) * 30, 30);
  const slot = WIDTH / days.length;
  const barWidth = Math.max(slot * 0.62, 2);
  const innerHeight = HEIGHT - 2 * PAD;

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: HEIGHT }} preserveAspectRatio="none" role="img" aria-label={t("workout.chartTitle")}>
        {days.map((day, index) => {
          const height = day.minutes > 0 ? Math.max((day.minutes / max) * innerHeight, 2) : 1;
          return (
            <rect
              key={day.date}
              x={index * slot + (slot - barWidth) / 2}
              y={HEIGHT - PAD - height}
              width={barWidth}
              height={height}
              rx={2}
              className="fill-primary"
              opacity={day.minutes > 0 ? 0.9 : 0.08}
            >
              <title>{`${pointLabel(day, locale)} · ${formatDuration(t, day.minutes)} · ${day.count}×`}</title>
            </rect>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>{formatDate(days[0].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
        <span>{formatDuration(t, max)}</span>
        <span>{formatDate(days[days.length - 1].end_date ?? days[days.length - 1].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
      </div>
    </div>
  );
}

/** Daily average stress (1-5) as bars colored by level, with a tick at the day's peak rating. */
export function StressBars({ days, locale }: { days: (Pick<StressDay, "date" | "average" | "max" | "count"> & { end_date?: string })[]; locale: string }) {
  const { t } = useTranslation();
  if (days.length === 0) return null;

  const slot = WIDTH / days.length;
  const barWidth = Math.max(slot * 0.62, 2);
  const innerHeight = HEIGHT - 2 * PAD;
  const y = (value: number) => HEIGHT - PAD - (value / 5) * innerHeight;

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: HEIGHT }} preserveAspectRatio="none" role="img" aria-label={t("stress.chartTitle")}>
        <line
          x1={PAD}
          x2={WIDTH - PAD}
          y1={y(3)}
          y2={y(3)}
          className="stroke-muted/30"
          strokeWidth={1}
          strokeDasharray="2 4"
        />
        {days.map((day, index) => {
          const x = index * slot + (slot - barWidth) / 2;
          if (day.average === null) {
            return <rect key={day.date} x={x} y={HEIGHT - PAD - 1} width={barWidth} height={1} className="fill-muted" opacity={0.2} />;
          }
          const top = y(day.average);
          return (
            <g key={day.date}>
              <rect
                x={x}
                y={top}
                width={barWidth}
                height={HEIGHT - PAD - top}
                rx={2}
                className={stressFillClass(day.average)}
                opacity={0.9}
              >
                <title>{`${pointLabel(day, locale)} · ${day.average.toFixed(1)} · ${day.count}×`}</title>
              </rect>
              {day.max !== null && day.max > day.average && (
                <line
                  x1={x}
                  x2={x + barWidth}
                  y1={y(day.max)}
                  y2={y(day.max)}
                  className="stroke-text"
                  strokeWidth={1.5}
                />
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>{formatDate(days[0].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
        <span>{t("stress.chartScale")}</span>
        <span>{formatDate(days[days.length - 1].end_date ?? days[days.length - 1].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
      </div>
    </div>
  );
}

/** Daily screen time as bars; the inner (amber) bar is the usage in the 2 hours before bed. */
export function ScreenTimeBars({
  days,
  locale,
}: {
  days: { date: string; end_date?: string; total: number | null; beforeBed: number | null }[];
  locale: string;
}) {
  const { t } = useTranslation();
  if (days.length === 0) return null;

  const highest = Math.max(...days.map((day) => day.total ?? 0), 240);
  const max = Math.ceil(highest / 60) * 60;
  const slot = WIDTH / days.length;
  const barWidth = Math.max(slot * 0.62, 2);
  const innerHeight = HEIGHT - 2 * PAD;
  const heightOf = (minutes: number) => Math.max((minutes / max) * innerHeight, 1);

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" style={{ height: HEIGHT }} preserveAspectRatio="none" role="img" aria-label={t("screen.chartTitle")}>
        {days.map((day, index) => {
          const x = index * slot + (slot - barWidth) / 2;
          if (day.total === null) {
            return (
              <rect key={day.date} x={x} y={HEIGHT - PAD - 1} width={barWidth} height={1} className="fill-muted" opacity={0.2} />
            );
          }
          const totalHeight = heightOf(day.total);
          const bedHeight = day.beforeBed ? Math.min(heightOf(day.beforeBed), totalHeight) : 0;
          const bed = day.beforeBed ? ` · ${t("screen.beforeBedShort", { duration: formatDuration(t, Math.round(day.beforeBed)) })}` : "";
          return (
            <g key={day.date}>
              <rect x={x} y={HEIGHT - PAD - totalHeight} width={barWidth} height={totalHeight} rx={2} className="fill-primary" opacity={0.55}>
                <title>{`${pointLabel(day, locale)} · ${formatDuration(t, Math.round(day.total))}${bed}`}</title>
              </rect>
              {bedHeight > 0 && (
                <rect x={x} y={HEIGHT - PAD - bedHeight} width={barWidth} height={bedHeight} rx={2} className="fill-warning" />
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>{formatDate(days[0].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
        <span>{formatDuration(t, max)}</span>
        <span>{formatDate(days[days.length - 1].end_date ?? days[days.length - 1].date, locale, { day: "numeric", month: "short", year: "numeric" })}</span>
      </div>
      <div className="mt-2 flex gap-4 text-xs text-muted">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-primary/60" />
          {t("screen.legendTotal")}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-warning" />
          {t("screen.legendBed")}
        </span>
      </div>
    </div>
  );
}
