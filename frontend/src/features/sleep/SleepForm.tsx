import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../lib/api";
import { formatDuration, toLocalInput } from "../../lib/format";

export interface SleepFormValues {
  started_at: string; // ISO string
  ended_at: string; // ISO string
}

/** Default bedtime / wake-up time for a retroactive entry about `dateIso`. */
export function dayDefaults(dateIso: string): SleepFormValues {
  const [year, month, day] = dateIso.split("-").map(Number);
  return {
    started_at: new Date(year, month - 1, day - 1, 23, 0).toISOString(),
    ended_at: new Date(year, month - 1, day, 7, 0).toISOString(),
  };
}

function lastNightDefaults(): { start: string; end: string } {
  const now = new Date();
  const end = new Date(now);
  end.setHours(7, 0, 0, 0);
  if (end.getTime() > now.getTime()) end.setDate(end.getDate() - 1);
  const start = new Date(end);
  start.setDate(start.getDate() - 1);
  start.setHours(23, 0, 0, 0);
  return { start: toLocalInput(start), end: toLocalInput(end) };
}

export function SleepForm({
  title,
  initial,
  busy,
  error,
  onSubmit,
  onCancel,
}: {
  title: string;
  initial?: SleepFormValues;
  busy: boolean;
  error: unknown;
  onSubmit: (values: SleepFormValues) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [fallback] = useState(lastNightDefaults);
  const [start, setStart] = useState(
    initial ? toLocalInput(new Date(initial.started_at)) : fallback.start,
  );
  const [end, setEnd] = useState(
    initial ? toLocalInput(new Date(initial.ended_at)) : fallback.end,
  );
  const [localError, setLocalError] = useState<string | null>(null);

  const code = error instanceof ApiError ? error.code : null;
  const message =
    localError ??
    (code === "invalid_time"
      ? t("sleep.invalidTime")
      : code === "overlap"
        ? t("sleep.overlap")
        : code === "too_long"
          ? t("sleep.tooLong")
          : error
          ? t("common.error")
          : null);

  const minutes = Math.round(
    (new Date(end).getTime() - new Date(start).getTime()) / 60_000,
  );

  function submit() {
    const startedAt = new Date(start);
    const endedAt = new Date(end);
    if (
      Number.isNaN(startedAt.getTime()) ||
      Number.isNaN(endedAt.getTime()) ||
      endedAt <= startedAt
    ) {
      setLocalError(t("sleep.invalidRange"));
      return;
    }
    setLocalError(null);
    onSubmit({ started_at: startedAt.toISOString(), ended_at: endedAt.toISOString() });
  }

  return (
    <div className="mt-4 rounded-2xl border border-muted/20 p-4">
      <p className="font-medium">{title}</p>
      <label className="mt-3 block text-sm text-muted">
        {t("sleep.startedAt")}
        <input
          type="datetime-local"
          value={start}
          onChange={(event) => setStart(event.target.value)}
          className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
      </label>
      <label className="mt-3 block text-sm text-muted">
        {t("sleep.endedAt")}
        <input
          type="datetime-local"
          value={end}
          onChange={(event) => setEnd(event.target.value)}
          className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
      </label>
      {minutes > 0 && (
        <p className="mt-2 text-sm text-muted">
          {t("sleep.durationPreview", { duration: formatDuration(t, minutes) })}
        </p>
      )}
      {message && <p className="mt-2 text-sm text-danger">{message}</p>}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={submit}
          className="flex-1 rounded-2xl bg-primary py-3 font-semibold text-on-primary disabled:opacity-60"
        >
          {t("sleep.save")}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          className="flex-1 rounded-2xl border border-muted/30 py-3 font-medium text-muted"
        >
          {t("sleep.cancel")}
        </button>
      </div>
    </div>
  );
}
