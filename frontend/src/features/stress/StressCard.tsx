import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "../../components/ui";
import { addDays, isoDate } from "../../lib/format";
import { STRESS_LEVELS, stressSoftClass, stressTextClass } from "../../lib/stress";
import type { StressCategory, StressLevel, StressLog } from "../../types/api";
import { useDeleteStress, useLogStress, useStressHistory, useUpdateStress } from "./api";
import { CategoryPicker } from "./CategoryPicker";

export function StressCard() {
  const { t } = useTranslation();
  const today = isoDate(new Date());
  const stats = useStressHistory(today, today);
  const log = useLogStress();
  const update = useUpdateStress();
  const remove = useDeleteStress();
  const [last, setLast] = useState<StressLog | null>(null);

  const busy = log.isPending || update.isPending || remove.isPending;
  const failed = log.isError || update.isError || remove.isError;
  const day = stats.data?.[0];

  function tap(level: StressLevel) {
    log.mutate({ level }, { onSuccess: (created) => setLast(created) });
  }

  function chooseCategory(category: StressCategory | null) {
    if (!last) return;
    update.mutate({ id: last.id, category }, { onSuccess: (updated) => setLast(updated) });
  }

  function undo() {
    if (!last) return;
    remove.mutate(last.id, { onSuccess: () => setLast(null) });
  }

  if (stats.isPending) return <Skeleton />;
  if (stats.isError) return <QueryError error={stats.error} retry={() => void stats.refetch()} />;
  return (
    <Card>
      <h2 className="font-medium">{t("stress.title")}</h2>
      <p className="mt-1 text-sm text-muted">{t("stress.question")}</p>

      <div className="mt-3 grid grid-cols-5 gap-2">
        {STRESS_LEVELS.map((level) => (
          <button
            key={level}
            type="button"
            disabled={busy}
            aria-label={`${level} — ${t(`stress.levels.${level}`)}`}
            onClick={() => tap(level)}
            className={`rounded-2xl py-4 text-2xl font-semibold transition active:scale-95 disabled:opacity-60 ${stressSoftClass(level)} ${
              last?.level === level ? "ring-2 ring-current" : ""
            }`}
          >
            {level}
          </button>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>{t("stress.levels.1")}</span>
        <span>{t("stress.levels.5")}</span>
      </div>

      {last && (
        <div className="mt-4 rounded-2xl border border-muted/20 p-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm">
              {t("stress.saved", { level: last.level })}
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={undo}
              className="text-sm text-muted underline disabled:opacity-60"
            >
              {t("stress.undo")}
            </button>
          </div>
          <p className="mt-3 text-xs text-muted">{t("stress.categoryHint")}</p>
          <div className="mt-2">
            <CategoryPicker value={last.category} onChange={chooseCategory} disabled={busy} />
          </div>
        </div>
      )}

      {failed && <p className="mt-2 text-sm text-danger">{t("common.error")}</p>}

      <p className="mt-4 text-sm text-muted">
        {day && day.count > 0 && day.average !== null ? (
          <>
            {t("stress.today")}:{" "}
            <span className={`font-semibold ${stressTextClass(day.average)}`}>
              {day.average.toFixed(1)}
            </span>{" "}
            · {t("stress.count", { n: day.count })}
          </>
        ) : (
          t("stress.noToday")
        )}
      </p>
    </Card>
  );
}
