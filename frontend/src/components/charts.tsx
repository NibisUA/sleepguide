import { useTranslation } from "react-i18next";

import { formatDate, formatDuration } from "../lib/format";
import type { SleepDay } from "../types/api";

const WIDTH = 320;
const HEIGHT = 104;
const PAD = 8;

/** Nightly sleep duration as bars, with a dashed sleep-goal line. */
export function DurationBars({
  days,
  goal,
  locale,
}: {
  days: SleepDay[];
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
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img">
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
              <title>{`${formatDate(day.date, locale)} · ${formatDuration(t, day.sleep_minutes)}`}</title>
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
        <span>{formatDate(days[0].date, locale)}</span>
        <span className="text-warning">{t("history.goal", { value: formatDuration(t, goal) })}</span>
        <span>{formatDate(days[days.length - 1].date, locale)}</span>
      </div>
    </div>
  );
}

/** Sleep Score over time with the 70 / 85 band markers. */
export function ScoreLine({ days, locale }: { days: SleepDay[]; locale: string }) {
  const { t } = useTranslation();
  const withScore = days.filter((day) => day.score !== null);
  if (withScore.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">{t("history.noScore")}</p>;
  }

  const step = days.length > 1 ? (WIDTH - 2 * PAD) / (days.length - 1) : 0;
  const x = (index: number) => PAD + index * step;
  const y = (score: number) => HEIGHT - PAD - (score / 100) * (HEIGHT - 2 * PAD);
  const path = days
    .map((day, index) => (day.score === null ? null : `${x(index)},${y(day.score)}`))
    .filter((point): point is string => point !== null)
    .map((point, index) => `${index === 0 ? "M" : "L"}${point}`)
    .join(" ");

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full" role="img">
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
              <title>{`${formatDate(day.date, locale)} · ${day.score}`}</title>
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
