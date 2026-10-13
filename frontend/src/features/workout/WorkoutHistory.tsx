import { useRepeatWorkout } from "./Templates";
import { WriteError } from "../records/WriteError";
import { QueryError, Skeleton } from "../../components/QueryState";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { MinutesBars } from "../../components/charts";
import { confirmAction } from "../../lib/confirm";
import { formatDate, formatDuration, formatTime } from "../../lib/format";
import type { HistoryOverview, Workout } from "../../types/api";
import {
  useCreateWorkout,
  useDeleteWorkout,
  useUpdateWorkout,
  type WorkoutFormValues,
} from "./api";
import { INTENSITY_COLOR, TYPE_ICON } from "./meta";
import { WorkoutForm } from "./WorkoutForm";
import { useHistoryEntries, workoutPoints } from "../history/api";
import { BucketNote, ChartScroll, EntryPager } from "../history/HistoryControls";
import { ExerciseLogsSheet } from "../records/ExerciseLogsSheet";

export function WorkoutHistory({ overview }: { overview: HistoryOverview }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language;
  const list = useHistoryEntries("workout", overview.from_date, overview.to_date);
  const create = useCreateWorkout();
  const update = useUpdateWorkout();
  const remove = useDeleteWorkout();
  const repeat = useRepeatWorkout();

  const [editing, setEditing] = useState<Workout | null>(null);
  const [creating, setCreating] = useState(false);
  const [exerciseWorkout, setExerciseWorkout] = useState<Workout | null>(null);

  const days = workoutPoints(overview);
  const totalCount = overview.workout.count;
  const totalMinutes = overview.workout.minutes;
  const finished = list.data?.pages.flatMap(page => page.workouts) ?? [];

  function closeForm() {
    setEditing(null);
    setCreating(false);
  }

  function save(values: WorkoutFormValues) {
    if (editing) update.mutate({ id: editing.id, ...values }, { onSuccess: closeForm });
    else create.mutate(values, { onSuccess: workout => { closeForm(); setExerciseWorkout(workout); } });
  }

  async function deleteWorkout(workout: Workout) {
    if (await confirmAction(t("workout.deleteConfirm"))) {
      remove.mutate(workout.id, { onSuccess: closeForm });
    }
  }

  if (list.isPending) return <Skeleton />;
  if (list.isError && !list.data) return <QueryError error={list.error} retry={() => void list.refetch()} />;

  return (
    <section className="rounded-3xl bg-surface p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">{t("workout.historyTitle")}</h2>
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setCreating(true);
          }}
          className="rounded-full bg-primary px-3 py-1.5 text-sm font-medium text-on-primary"
        >
          {t("workout.add")}
        </button>
      </div>

      {(creating || editing) && (
        <WorkoutForm
          key={editing ? editing.id : "new"}
          title={editing ? t("workout.formEditTitle") : t("workout.formTitle")}
          initial={
            editing
              ? {
                  started_at: editing.started_at,
                  ended_at: editing.ended_at ?? editing.started_at,
                  type: editing.type,
                  intensity: editing.intensity,
                }
              : undefined
          }
          busy={create.isPending || update.isPending}
          error={editing ? update.error : create.error}
          onSubmit={save}
          onCancel={closeForm}
        />
      )}

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("workout.totalCount")}</p>
          <p className="mt-1 text-2xl font-semibold">{totalCount}</p>
        </div>
        <div className="rounded-2xl bg-bg p-3">
          <p className="text-xs text-muted">{t("workout.totalTime")}</p>
          <p className="mt-1 text-2xl font-semibold">
            {totalMinutes > 0 ? formatDuration(t, totalMinutes) : "—"}
          </p>
        </div>
      </div>

      <>
          <p className="mt-5 text-sm text-muted">{t("workout.chartTitle")}</p>
          <BucketNote overview={overview} kind="workout" /><ChartScroll count={days.length}><MinutesBars days={days} locale={locale} /></ChartScroll>
        </>

      {finished.length === 0 && !list.isPending ? (
        <p className="mt-4 text-sm text-muted">{t("workout.noWorkouts")}</p>
      ) : (
        <ul className="mt-3 divide-y divide-muted/10">
          {finished.map((workout) => (
            <li key={workout.id} className="py-3">
              <div className="min-w-0">
                <p className="text-sm">
                  {TYPE_ICON[workout.type]} {t(`workout.types.${workout.type}`)}{" "}
                  <span className="text-muted">
                    {formatDuration(t, workout.duration_minutes ?? 0)}
                  </span>
                  <span className={`ml-1 text-xs ${INTENSITY_COLOR[workout.intensity]}`}>
                    · {t(`workout.intensities.${workout.intensity}`)}
                  </span>
                </p>
                <p className="text-xs text-muted">
                  {formatDate(workout.local_date, locale, { day: "numeric", month: "short", year: "numeric" })} ·{" "}
                  {formatTime(workout.started_at, locale)}
                  {workout.ended_at ? ` → ${formatTime(workout.ended_at, locale)}` : ""}
                </p>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm">
                <button type="button" disabled={repeat.isPending} className="min-h-11 text-primary" onClick={() => repeat.mutate(workout.id, { onSuccess: setExerciseWorkout })}>{t("templates.repeat")}</button>
                <button type="button" onClick={() => setExerciseWorkout(workout)} className="min-h-11 text-primary">{t("records.resultsButton")}</button>
                <button
                  type="button"
                  onClick={() => {
                    setCreating(false);
                    setEditing(workout);
                  }}
                  className="text-primary"
                >
                  {t("workout.edit")}
                </button>
                <button
                  type="button"
                  disabled={remove.isPending}
                  onClick={() => void deleteWorkout(workout)}
                  className="text-danger disabled:opacity-60"
                >
                  {t("workout.delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <EntryPager kind="workout" query={list} />
      <WriteError error={repeat.error} />
      {remove.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}</p>}
      {exerciseWorkout && <ExerciseLogsSheet workout={exerciseWorkout} onClose={() => setExerciseWorkout(null)} />}
    </section>
  );
}
