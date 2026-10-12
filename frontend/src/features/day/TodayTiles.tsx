import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { formatDuration, isoDate } from "../../lib/format";
import { stressTextClass } from "../../lib/stress";
import { useDaySummary } from "./api";
import { DaySummarySheet } from "./DaySummarySheet";

function Tile({ icon, label, value, valueClass = "" }: { icon: string; label: string; value: string; valueClass?: string }) {
  return (
    <div className="rounded-2xl bg-surface p-3">
      <p className="text-xs text-muted">
        {icon} {label}
      </p>
      <p className={`mt-1 truncate text-lg font-semibold ${valueClass}`}>{value}</p>
    </div>
  );
}

/** Three at-a-glance tiles for today; tapping them opens the Daily Summary. */
export function TodayTiles() {
  const { t } = useTranslation();
  const today = isoDate(new Date());
  const query = useDaySummary(today);
  const [open, setOpen] = useState(false);
  const day = query.data;

  const workout = day && day.workouts.length > 0 ? formatDuration(t, day.workout_minutes) : "—";
  const stressValue = day && day.stress.average !== null ? day.stress.average.toFixed(1) : "—";
  const screen = day?.screen_time ? formatDuration(t, day.screen_time.total_minutes) : "—";

  if (query.isPending) return <Skeleton />;
  if (query.isError) return <QueryError error={query.error} retry={() => void query.refetch()} />;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t("day.openToday")}
        className="grid w-full grid-cols-3 gap-3 text-left"
      >
        <Tile icon="🏋️" label={t("day.tileWorkout")} value={workout} />
        <Tile
          icon="🧠"
          label={t("day.tileStress")}
          value={stressValue}
          valueClass={day && day.stress.average !== null ? stressTextClass(day.stress.average) : "text-muted"}
        />
        <Tile icon="📱" label={t("day.tileScreen")} value={screen} />
      </button>
      {open && <DaySummarySheet date={today} onClose={() => setOpen(false)} />}
    </>
  );
}
