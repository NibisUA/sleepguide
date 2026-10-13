import { Templates } from "./Templates";
import { useState } from "react";
import { QueryError, Skeleton } from "../../components/QueryState";
import { useTranslation } from "react-i18next";

import { Card, PrimaryButton } from "../../components/ui";
import { confirmAction } from "../../lib/confirm";
import { ApiError } from "../../lib/api";
import { formatClock, formatTime, toLocalInput } from "../../lib/format";
import { useNow } from "../../lib/useNow";
import type { Workout, WorkoutIntensity, WorkoutType } from "../../types/api";
import {
  useCurrentWorkout,
  useDeleteWorkout,
  useStartWorkout,
  useStopWorkout,
} from "./api";
import { DEFAULT_INTENSITY, DEFAULT_TYPE, FORGOTTEN_WORKOUT_MINUTES, TYPE_ICON } from "./meta";
import { IntensityPicker, TypePicker } from "./Pickers";
import { ExerciseLogsSheet } from "../records/ExerciseLogsSheet";

function EndTimePicker({
  busy,
  errorKey,
  onConfirm,
}: {
  busy: boolean;
  errorKey: string | null;
  onConfirm: (iso: string) => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState(() => toLocalInput(new Date()));
  return (
    <div className="mt-4">
      <p className="font-medium">{t("workout.endTitle")}</p>
      <p className="mt-1 text-sm text-muted">{t("workout.endHint")}</p>
      <input
        type="datetime-local"
        value={value}
        max={toLocalInput(new Date())}
        onChange={(event) => setValue(event.target.value)}
        className="mt-3 w-full rounded-xl border border-muted/30 bg-bg p-3 text-text"
      />
      {errorKey && <p className="mt-2 text-sm text-danger">{t(errorKey)}</p>}
      <PrimaryButton
        disabled={busy || !value}
        onClick={() => onConfirm(new Date(value).toISOString())}
      >
        {t("workout.confirm")}
      </PrimaryButton>
    </div>
  );
}

function Running({ workout }: { workout: Workout }) {
  const { t, i18n } = useTranslation();
  const now = useNow(1000);
  const stop = useStopWorkout();
  const discard = useDeleteWorkout();
  const [showSets, setShowSets] = useState((workout.planned_sets?.length ?? 0) > 0);
  const [type, setType] = useState<WorkoutType>(workout.type);
  const [intensity, setIntensity] = useState<WorkoutIntensity>(workout.intensity);

  const elapsedSeconds = (now.getTime() - new Date(workout.started_at).getTime()) / 1000;
  const err = stop.error instanceof ApiError ? stop.error : null;
  const needsEndTime =
    elapsedSeconds / 60 > FORGOTTEN_WORKOUT_MINUTES || err?.code === "end_time_required";
  const errorKey =
    err?.code === "invalid_time"
      ? "workout.invalidTime"
      : err?.code === "too_long"
        ? "workout.tooLong"
        : null;
  const showGenericError =
    err !== null && !["end_time_required", "invalid_time", "too_long"].includes(err.code);

  async function discardWorkout() {
    if (await confirmAction(t("workout.discardConfirm"))) discard.mutate(workout.id);
  }

  return (
    <Card>
      <p className="text-sm text-muted">
        {TYPE_ICON[type]} {t("workout.inProgress")}
      </p>
      <p className="mt-1 text-5xl font-semibold tabular-nums">{formatClock(elapsedSeconds)}</p>
      <p className="mt-1 text-sm text-muted">
        {t("workout.startedAt", { time: formatTime(workout.started_at, i18n.language) })}
      </p>

      <p className="mt-4 text-sm text-muted">{t("workout.type")}</p>
      <div className="mt-2">
        <TypePicker value={type} onChange={setType} disabled={stop.isPending} />
      </div>
      <p className="mt-4 text-sm text-muted">{t("workout.intensity")}</p>
      <div className="mt-2">
        <IntensityPicker value={intensity} onChange={setIntensity} disabled={stop.isPending} />
      </div>

      {needsEndTime ? (
        <EndTimePicker
          busy={stop.isPending}
          errorKey={errorKey}
          onConfirm={(iso) => stop.mutate({ ended_at: iso, type, intensity })}
        />
      ) : (
        <>
          <PrimaryButton disabled={stop.isPending} onClick={() => stop.mutate({ type, intensity })}>
            {t("workout.finish")}
          </PrimaryButton>
          {errorKey && <p className="mt-2 text-sm text-danger">{t(errorKey)}</p>}
        </>
      )}
      {showGenericError && <p className="mt-2 text-sm text-danger">{t("common.error")}</p>}

      <button
        type="button"
        disabled={discard.isPending || stop.isPending}
        onClick={() => void discardWorkout()}
        className="mt-3 w-full text-center text-sm text-muted disabled:opacity-60"
      >
        {t("workout.discard")}
      </button>
      {discard.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}</p>}
      <button type="button" onClick={() => setShowSets(true)} className="mt-3 w-full rounded-xl border border-primary/50 py-3 text-primary">{t("records.logDuringWorkout")}</button>
      {showSets && <ExerciseLogsSheet workout={workout} onClose={() => setShowSets(false)} />}
    </Card>
  );
}

function Idle() {
  const { t } = useTranslation();
  const start = useStartWorkout();
  const [type, setType] = useState<WorkoutType>(DEFAULT_TYPE);
  return (
    <Card>
      <h2 className="font-medium">{t("workout.title")}</h2>
      <div className="mt-3">
        <TypePicker value={type} onChange={setType} disabled={start.isPending} />
      </div>
      <PrimaryButton
        disabled={start.isPending}
        onClick={() => start.mutate({ type, intensity: DEFAULT_INTENSITY })}
      >
        {t("workout.start")}
      </PrimaryButton>
      {start.isError && <p className="mt-2 text-sm text-danger">{t("common.error")}</p>}
      <Templates />
    </Card>
  );
}

export function WorkoutCard() {
  const { t } = useTranslation();
  const current = useCurrentWorkout();
  if (current.isPending) return <Skeleton />;
  if (current.isError) return <QueryError error={current.error} retry={() => void current.refetch()} />;
  return current.data ? <Running workout={current.data} /> : <Idle />;
}
