import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "../../components/ui";
import { addDays, formatDuration, isoDate } from "../../lib/format";
import type { ScreenTime } from "../../types/api";
import { usePutScreenTime, useScreenTimeRange } from "./api";
import { ScreenTimeForm } from "./ScreenTimeForm";

function Summary({ label, record }: { label: string; record: ScreenTime | undefined }) {
  const { t } = useTranslation();
  return (
    <p className="mt-2 text-sm">
      <span className="text-muted">{label}: </span>
      {record ? (
        <>
          <span className="font-semibold">{formatDuration(t, record.total_minutes)}</span>
          {record.before_bed_minutes !== null && (
            <span className="text-muted">
              {" "}
              · {t("screen.beforeBedShort", { duration: formatDuration(t, record.before_bed_minutes) })}
            </span>
          )}
        </>
      ) : (
        <span className="text-muted">—</span>
      )}
    </p>
  );
}

export function ScreenTimeCard() {
  const { t } = useTranslation();
  const today = isoDate(new Date());
  const yesterday = addDays(today, -1);
  const range = useScreenTimeRange(addDays(today, -13), today);
  const save = usePutScreenTime();
  const [formDate, setFormDate] = useState<string | null>(null);

  const records = range.data ?? [];
  const todays = records.find((record) => record.local_date === today);
  const yesterdays = records.find((record) => record.local_date === yesterday);

  if (range.isPending) return <Skeleton />;
  if (range.isError) return <QueryError error={range.error} retry={() => void range.refetch()} />;
  return (
    <Card>
      <h2 className="font-medium">{t("screen.title")}</h2>
      <Summary label={t("screen.today")} record={todays} />
      <Summary label={t("screen.yesterday")} record={yesterdays} />

      {formDate === null ? (
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={() => setFormDate(yesterdays ? today : yesterday)}
            className="flex-1 rounded-2xl bg-primary py-3 font-semibold text-on-primary"
          >
            {yesterdays ? t("screen.addToday") : t("screen.addYesterday")}
          </button>
          <button
            type="button"
            onClick={() => setFormDate(today)}
            className="rounded-2xl border border-muted/30 px-4 py-3 text-sm text-muted"
          >
            {t("screen.otherDay")}
          </button>
        </div>
      ) : (
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
    </Card>
  );
}
