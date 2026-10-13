import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../lib/api";
import { joinMinutes, splitMinutes } from "../../lib/duration";
import { addDays, isoDate } from "../../lib/format";
import type { ScreenTime } from "../../types/api";
import { useScreenTimeRange, type ScreenTimeInput } from "./api";
import { DurationInput } from "./DurationInput";
import { categoryDistribution, SCREEN_CATEGORIES, type CategoryField, type ScreenCategories } from "./categories";
import { CategoryBreakdown } from "./CategoryBreakdown";
import { lazy, Suspense } from "react";
const ScreenshotImport = lazy(() => import("./ScreenshotImport").then(m => ({ default: m.ScreenshotImport })));

const MAX_BEFORE_BED = 120;

export function ScreenTimeForm({
  title,
  initialDate,
  records,
  busy,
  error,
  onSubmit,
  onCancel,
}: {
  title: string;
  initialDate: string;
  records: ScreenTime[]; // known days, used to prefill when the date changes
  busy: boolean;
  error: unknown;
  onSubmit: (values: ScreenTimeInput) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const today = isoDate(new Date());

  const prefill = (date: string) => {
    const record = records.find((item) => item.local_date === date);
    return {
      total: splitMinutes(record ? record.total_minutes : null),
      bed: splitMinutes(record ? record.before_bed_minutes : null),
      categories: Object.fromEntries(SCREEN_CATEGORIES.map(({ field }) => [field, splitMinutes(record?.[field] ?? null)])) as Record<CategoryField, ReturnType<typeof splitMinutes>>,
    };
  };

  const [date, setDate] = useState(initialDate);
  const [total, setTotal] = useState(() => prefill(initialDate).total);
  const [bed, setBed] = useState(() => prefill(initialDate).bed);
  const [categories, setCategories] = useState(() => prefill(initialDate).categories);
  const [changedCategories, setChangedCategories] = useState<Set<CategoryField>>(new Set());
  const [localError, setLocalError] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [imported, setImported] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const knownRecord = records.find(r => r.local_date === date);
  const checkStored = imported && !knownRecord && /^\d{4}-\d{2}-\d{2}$/.test(date);
  const stored = useScreenTimeRange(date, date, checkStored);
  const existingRecord = knownRecord ?? stored.data?.[0];

  const code = error instanceof ApiError ? error.code : null;
  const message =
    localError ??
    (code === "invalid_screen_categories" ? t("screen.categoriesInvalid") : code === "invalid_screen_time"
      ? t("screen.invalidUsage")
      : code === "invalid_date"
        ? t("screen.invalidDate")
        : error
          ? t("common.error")
          : null);

  function changeDate(next: string) {
    setDate(next);
    const values = prefill(next);
    if (!imported) setTotal(values.total);
    if (!imported) { setCategories(values.categories); setChangedCategories(new Set()); }
    setBed(values.bed);
    setLocalError(null);
    setOverwrite(false);
  }

  function submit() {
    const totalMinutes = joinMinutes(total.hours, total.minutes);
    const bedMinutes = joinMinutes(bed.hours, bed.minutes);
    const categoryMinutes: ScreenCategories = {};
    for (const { field } of SCREEN_CATEGORIES) {
      const value = joinMinutes(categories[field].hours, categories[field].minutes);
      if (value !== null || changedCategories.has(field)) categoryMinutes[field] = value;
    }
    if (!date) {
      setLocalError(t("screen.invalidDate"));
      return;
    }
    if (totalMinutes === null || Number.isNaN(totalMinutes) || totalMinutes > 24 * 60) {
      setLocalError(t("screen.invalidTotal"));
      return;
    }
    if (bedMinutes !== null && (Number.isNaN(bedMinutes) || bedMinutes > MAX_BEFORE_BED || bedMinutes > totalMinutes)) {
      setLocalError(t("screen.invalidUsage"));
      return;
    }
    if (Object.values(categoryMinutes).some(value => value !== null && (!Number.isFinite(value) || value < 0 || value > 1440)) || categoryDistribution(totalMinutes, categoryMinutes).remaining < 0) {
      setLocalError(t("screen.categoriesInvalid")); return;
    }
    setLocalError(null);
    if (checkStored && (stored.isPending || stored.isError)) { setLocalError(t(stored.isError ? "common.error" : "common.loading")); return; }
    if (imported && existingRecord && !overwrite) { setLocalError(t("ocr.overwriteRequired")); return; }
    onSubmit({ date, total_minutes: totalMinutes, before_bed_minutes: bedMinutes, ...categoryMinutes });
  }

  return (
    <div className="mt-4 rounded-2xl border border-muted/20 p-4">
      <p className="font-medium">{title}</p>
      <button type="button" disabled={busy} onClick={() => setImportOpen(true)} className="mt-3 w-full rounded-xl border border-primary/40 p-3 text-sm text-primary">{t("ocr.title")}</button>
      {importOpen && <Suspense fallback={<p role="status" className="mt-3 text-muted">{t("ocr.loading")}</p>}><ScreenshotImport onClose={() => setImportOpen(false)} onPick={(minutes, detected) => {
        setTotal(splitMinutes(minutes)); setImported(true); setOverwrite(false); setImportOpen(false); setLocalError(null);
        setCategories(Object.fromEntries(SCREEN_CATEGORIES.map(({ field }) => [field, splitMinutes(detected?.[field] ?? null)])) as typeof categories);
        setChangedCategories(new Set(SCREEN_CATEGORIES.filter(({ field }) => detected?.[field] != null || joinMinutes(categories[field].hours, categories[field].minutes) !== null).map(({ field }) => field)));
      }} /></Suspense>}
      {imported && <p className="mt-3 text-xs text-primary">{t("ocr.review")}</p>}

      <label className="mt-3 block text-sm text-muted">
        {t("screen.dateLabel")}
        <input
          type="date"
          value={date}
          min={addDays(today, -365)}
          max={today}
          disabled={busy}
          onChange={(event) => changeDate(event.target.value)}
          className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
      </label>

      <p className="mt-3 text-sm text-muted">{t("screen.totalLabel")}</p>
      <div className="mt-2">
        <DurationInput
          hours={total.hours}
          minutes={total.minutes}
          disabled={busy}
          onChange={(hours, minutes) => setTotal({ hours, minutes })}
        />
      </div>

      <p className="mt-4 text-sm font-medium">{t("screen.categoriesTitle")}</p>
      <p className="mt-1 text-xs text-muted">{t("screen.categoriesHint")}</p>
      <div className="mt-3 space-y-3">
        {SCREEN_CATEGORIES.map(({ field, textColor }) => <fieldset key={field}>
          <legend className={`mb-1 text-sm ${textColor}`}>{t(`screen.categoryLabels.${field}`)}</legend>
          <DurationInput label={t(`screen.categoryLabels.${field}`)} hours={categories[field].hours} minutes={categories[field].minutes} disabled={busy}
            onChange={(hours, minutes) => { setCategories(prev => ({ ...prev, [field]: { hours, minutes } })); setChangedCategories(prev => new Set([...prev, field])); setLocalError(null); }} />
        </fieldset>)}
      </div>
      {joinMinutes(total.hours, total.minutes) !== null && Number.isFinite(joinMinutes(total.hours, total.minutes)) && <CategoryBreakdown total={joinMinutes(total.hours, total.minutes)!}
        categories={Object.fromEntries(SCREEN_CATEGORIES.map(({ field }) => [field, joinMinutes(categories[field].hours, categories[field].minutes)]))} />}

      <p className="mt-3 text-sm text-muted">{t("screen.beforeBedLabel")}</p>
      <div className="mt-2">
        <DurationInput
          hours={bed.hours}
          minutes={bed.minutes}
          disabled={busy}
          onChange={(hours, minutes) => setBed({ hours, minutes })}
        />
      </div>
      <p className="mt-1 text-xs text-muted">{t("screen.beforeBedHint")}</p>
      {checkStored && stored.isError && <button type="button" className="mt-3 text-sm text-primary" onClick={() => void stored.refetch()}>{t("common.retry")}</button>}
      {imported && existingRecord && <label className="mt-3 flex items-start gap-2 text-sm text-warning">
        <input type="checkbox" checked={overwrite} disabled={busy} onChange={e => setOverwrite(e.target.checked)} className="mt-1 accent-primary" />{t("ocr.overwrite")}
      </label>}

      {message && <p className="mt-2 text-sm text-danger">{message}</p>}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          disabled={busy || (checkStored && (stored.isPending || stored.isError))}
          onClick={submit}
          className="flex-1 rounded-2xl bg-primary py-3 font-semibold text-on-primary disabled:opacity-60"
        >
          {t("screen.save")}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          className="flex-1 rounded-2xl border border-muted/30 py-3 font-medium text-muted"
        >
          {t("screen.cancel")}
        </button>
      </div>
    </div>
  );
}
