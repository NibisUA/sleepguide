import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { formatDate, formatDuration, isoDate } from "../../lib/format";
import { heatmapColor } from "../../lib/score";
import type { SleepDay } from "../../types/api";

const CELL = 24;
const GAP = 3;

interface Cell {
  date: string;
  inYear: boolean;
  day: SleepDay | null;
}

function buildCells(year: number, byDate: Map<string, SleepDay>): Cell[] {
  const first = new Date(year, 0, 1);
  const offset = (first.getDay() + 6) % 7; // Monday-first column layout
  const cursor = new Date(year, 0, 1 - offset);
  const last = new Date(year, 11, 31);
  const cells: Cell[] = [];
  while (cursor <= last) {
    const iso = isoDate(cursor);
    cells.push({ date: iso, inYear: iso >= `${year}-01-01`, day: byDate.get(iso) ?? null });
    cursor.setDate(cursor.getDate() + 1);
  }
  return cells;
}

/** Yearly heatmap: columns are weeks, rows are weekdays; tap a day for details. */
export function YearHeatmap({
  year,
  days,
  selected,
  onSelect,
}: {
  year: number;
  days: SleepDay[];
  selected: string | null;
  onSelect: (date: string) => void;
}) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const byDate = new Map(days.map((day) => [day.date, day]));
  const cells = buildCells(year, byDate);
  const weeks = Math.ceil(cells.length / 7);
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const now = new Date();
    const target = year === now.getFullYear() ? isoDate(new Date(year, now.getMonth(), 1)) : `${year}-01-01`;
    const index = cells.findIndex(cell => cell.date === target);
    if (scroller.current && index >= 0) {
      scroller.current.scrollLeft = Math.max(0, 24 + Math.floor(index / 7) * (CELL + GAP) - 24);
    }
  }, [year]);

  const weekdayLabels = Array.from({ length: 7 }, (_, index) =>
    new Date(2024, 0, 1 + index).toLocaleDateString(locale, { weekday: "short" }),
  );

  const months = cells
    .map((cell, index) => ({ cell, index }))
    .filter(({ cell }) => cell.inYear && cell.date.endsWith("-01"))
    .map(({ cell, index }) => ({
      week: Math.floor(index / 7),
      label: formatDate(cell.date, locale, { month: "short" }),
    }));

  const label = (cell: Cell) => {
    const date = formatDate(cell.date, locale, { day: "numeric", month: "long" });
    if (cell.day?.score != null) return `${date} · ${cell.day.score}`;
    if (cell.day && cell.day.sleep_minutes > 0) {
      return `${date} · ${formatDuration(t, cell.day.sleep_minutes)}`;
    }
    return `${date} · ${t("history.noSleep")}`;
  };

  return (
    <div>
      <div ref={scroller} className="overflow-x-auto pb-1">
        <div className="relative" style={{ width: 24 + weeks * (CELL + GAP) }}>
          <div className="relative h-4">
            {months.map((month) => (
              <span
                key={month.week}
                className="absolute text-[10px] text-muted"
                style={{ left: 24 + month.week * (CELL + GAP) }}
              >
                {month.label}
              </span>
            ))}
          </div>
          <div className="flex">
            <div
              className="mr-1 flex flex-col justify-between text-[8px] leading-none text-muted"
              style={{ height: 7 * (CELL + GAP) - GAP }}
            >
              {weekdayLabels.map((weekday, index) => (
                <span key={index}>{index % 2 === 0 ? weekday : ""}</span>
              ))}
            </div>
            <div
              style={{
                display: "grid",
                gridAutoFlow: "column",
                gridTemplateRows: `repeat(7, ${CELL}px)`,
                gap: GAP,
              }}
            >
              {cells.map((cell) => (
                <button
                  key={cell.date}
                  type="button"
                  data-heatmap="true"
                  onClick={() => onSelect(cell.date)}
                  title={label(cell)}
                  aria-label={label(cell)}
                  aria-pressed={selected === cell.date}
                  disabled={!cell.inYear || cell.date > isoDate(new Date())}
                  style={{
                    width: CELL,
                    height: CELL,
                    borderRadius: 2,
                    opacity: cell.inYear ? 1 : 0.3,
                    background: cell.day ? heatmapColor(cell.day) : "rgba(113, 129, 122, 0.12)",
                    outline: selected === cell.date ? "1.5px solid var(--color-primary)" : "none",
                    outlineOffset: 1,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-1 text-[10px] text-muted">
        <span>{t("history.less")}</span>
        {[0.15, 0.35, 0.55, 0.75, 1].map((alpha) => (
          <span
            key={alpha}
            className="inline-block rounded-sm"
            style={{ width: CELL, height: CELL, background: `rgba(33, 216, 144, ${alpha})` }}
          />
        ))}
        <span>{t("history.more")}</span>
        <span className="ml-2 inline-flex items-center gap-1">
          <span
            className="inline-block rounded-sm"
            style={{ width: CELL, height: CELL, background: "rgba(229, 166, 58, 0.45)" }}
          />
          {t("sleep.nap")}
        </span>
      </div>
    </div>
  );
}
