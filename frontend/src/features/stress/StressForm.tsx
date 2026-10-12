import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../lib/api";
import { toLocalInput } from "../../lib/format";
import { STRESS_LEVELS, stressSoftClass } from "../../lib/stress";
import type { StressCategory, StressLevel } from "../../types/api";
import { CategoryPicker } from "./CategoryPicker";

export interface StressFormValues {
  level: StressLevel;
  category: StressCategory | null;
  logged_at: string; // ISO
}

export function StressForm({
  title,
  initial,
  busy,
  error,
  onSubmit,
  onCancel,
}: {
  title: string;
  initial?: StressFormValues;
  busy: boolean;
  error: unknown;
  onSubmit: (values: StressFormValues) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [level, setLevel] = useState<StressLevel>(initial?.level ?? 3);
  const [category, setCategory] = useState<StressCategory | null>(initial?.category ?? null);
  const [time, setTime] = useState(() =>
    toLocalInput(initial ? new Date(initial.logged_at) : new Date()),
  );
  const [localError, setLocalError] = useState<string | null>(null);

  const code = error instanceof ApiError ? error.code : null;
  const message =
    localError ??
    (code === "invalid_time" ? t("stress.invalidTime") : error ? t("common.error") : null);

  function submit() {
    const loggedAt = new Date(time);
    if (Number.isNaN(loggedAt.getTime())) {
      setLocalError(t("stress.invalidTime"));
      return;
    }
    setLocalError(null);
    onSubmit({ level, category, logged_at: loggedAt.toISOString() });
  }

  return (
    <div className="mt-4 rounded-2xl border border-muted/20 p-4">
      <p className="font-medium">{title}</p>

      <p className="mt-3 text-sm text-muted">{t("stress.levelLabel")}</p>
      <div className="mt-2 grid grid-cols-5 gap-2">
        {STRESS_LEVELS.map((value) => (
          <button
            key={value}
            type="button"
            disabled={busy}
            onClick={() => setLevel(value)}
            aria-label={`${value} — ${t(`stress.levels.${value}`)}`}
            aria-pressed={level === value}
            className={`rounded-xl py-3 text-xl font-semibold ${stressSoftClass(value)} ${
              level === value ? "ring-2 ring-current" : "opacity-60"
            }`}
          >
            {value}
          </button>
        ))}
      </div>

      <p className="mt-3 text-sm text-muted">{t("stress.categoryHint")}</p>
      <div className="mt-2">
        <CategoryPicker value={category} onChange={setCategory} disabled={busy} />
      </div>

      <label className="mt-3 block text-sm text-muted">
        {t("stress.timeLabel")}
        <input
          type="datetime-local"
          value={time}
          max={toLocalInput(new Date())}
          onChange={(event) => setTime(event.target.value)}
          className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
      </label>

      {message && <p className="mt-2 text-sm text-danger">{message}</p>}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={submit}
          className="flex-1 rounded-2xl bg-primary py-3 font-semibold text-on-primary disabled:opacity-60"
        >
          {t("stress.save")}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          className="flex-1 rounded-2xl border border-muted/30 py-3 font-medium text-muted"
        >
          {t("stress.cancel")}
        </button>
      </div>
    </div>
  );
}
