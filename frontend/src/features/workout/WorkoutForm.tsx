import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../lib/api";
import { formatDuration, toLocalInput } from "../../lib/format";
import type { WorkoutIntensity, WorkoutType } from "../../types/api";
import type { WorkoutFormValues } from "./api";
import { DEFAULT_INTENSITY, DEFAULT_TYPE } from "./meta";
import { IntensityPicker, TypePicker } from "./Pickers";

/** An hour-long workout ending now (default for a new retroactive entry). */
function recentDefaults(): { start: string; end: string } {
  const end = new Date();
  end.setSeconds(0, 0);
  const start = new Date(end.getTime() - 60 * 60_000);
  return { start: toLocalInput(start), end: toLocalInput(end) };
}

export function WorkoutForm({
  title,
  initial,
  busy,
  error,
  onSubmit,
  onCancel,
}: {
  title: string;
  initial?: WorkoutFormValues;
  busy: boolean;
  error: unknown;
  onSubmit: (values: WorkoutFormValues) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [fallback] = useState(recentDefaults);
  const [start, setStart] = useState(
    initial ? toLocalInput(new Date(initial.started_at)) : fallback.start,
  );
  const [end, setEnd] = useState(initial ? toLocalInput(new Date(initial.ended_at)) : fallback.end);
  const [type, setType] = useState<WorkoutType>(initial?.type ?? DEFAULT_TYPE);
  const [intensity, setIntensity] = useState<WorkoutIntensity>(
    initial?.intensity ?? DEFAULT_INTENSITY,
  );
  const [localError, setLocalError] = useState<string | null>(null);

  const code = error instanceof ApiError ? error.code : null;
  const message =
    localError ??
    (code === "invalid_time"
      ? t("workout.invalidTime")
      : code === "overlap"
        ? t("workout.overlap")
        : code === "too_long"
          ? t("workout.tooLong")
          : error
            ? t("common.error")
            : null);

  const minutes = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60_000);

  function submit() {
    const startedAt = new Date(start);
    const endedAt = new Date(end);
    if (
      Number.isNaN(startedAt.getTime()) ||
      Number.isNaN(endedAt.getTime()) ||
      endedAt <= startedAt
    ) {
      setLocalError(t("workout.invalidRange"));
      return;
    }
    setLocalError(null);
    onSubmit({
      started_at: startedAt.toISOString(),
      ended_at: endedAt.toISOString(),
      type,
      intensity,
    });
  }

  return (
    <div className="mt-4 rounded-2xl border border-muted/20 p-4">
      <p className="font-medium">{title}</p>

      <p className="mt-3 text-sm text-muted">{t("workout.type")}</p>
      <div className="mt-2">
        <TypePicker value={type} onChange={setType} disabled={busy} />
      </div>
      <p className="mt-3 text-sm text-muted">{t("workout.intensity")}</p>
      <div className="mt-2">
        <IntensityPicker value={intensity} onChange={setIntensity} disabled={busy} />
      </div>

      <label className="mt-3 block text-sm text-muted">
        {t("workout.startedAtLabel")}
        <input
          type="datetime-local"
          value={start}
          onChange={(event) => setStart(event.target.value)}
          className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
      </label>
      <label className="mt-3 block text-sm text-muted">
        {t("workout.endedAtLabel")}
        <input
          type="datetime-local"
          value={end}
          onChange={(event) => setEnd(event.target.value)}
          className="mt-1 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
        />
      </label>
      {minutes > 0 && (
        <p className="mt-2 text-sm text-muted">
          {t("workout.durationPreview", { duration: formatDuration(t, minutes) })}
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
          {t("workout.save")}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onCancel}
          className="flex-1 rounded-2xl border border-muted/30 py-3 font-medium text-muted"
        >
          {t("workout.cancel")}
        </button>
      </div>
    </div>
  );
}
