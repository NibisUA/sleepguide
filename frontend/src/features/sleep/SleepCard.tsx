import { useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import { QueryError, Skeleton } from "../../components/QueryState";
import { useTranslation } from "react-i18next";

import { ApiError } from "../../lib/api";
import { confirmAction } from "../../lib/confirm";
import { formatDuration, formatTime, toLocalInput } from "../../lib/format";
import { useNow } from "../../lib/useNow";
import type { SleepSession } from "../../types/api";
import {
  useCreateSleep,
  useCurrentSleep,
  useDeleteSleep,
  useSleepList,
  useStartSleep,
  useStopSleep,
  useUpdateSleep,
} from "./api";
import { SleepForm, type SleepFormValues } from "./SleepForm";

const FORGOTTEN_STOP_MINUTES = 14 * 60;

function Card({ children }: { children: ReactNode }) {
  return <section className="rounded-3xl bg-surface p-5">{children}</section>;
}

function PrimaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="mt-4 w-full rounded-2xl bg-primary py-4 text-lg font-semibold text-on-primary transition active:scale-[0.98] disabled:opacity-60"
    />
  );
}

function SecondaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="mt-2 w-full rounded-2xl border border-muted/30 py-3 font-medium text-text transition active:scale-[0.98] disabled:opacity-60"
    />
  );
}

function WakeTimePicker({
  onConfirm,
  busy,
  errorKey,
}: {
  onConfirm: (iso: string) => void;
  busy: boolean;
  errorKey: string | null;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState(() => toLocalInput(new Date()));
  return (
    <div className="mt-4">
      <p className="font-medium">{t("sleep.wakeTitle")}</p>
      <p className="mt-1 text-sm text-muted">{t("sleep.wakeHint")}</p>
      <input
        type="datetime-local"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="mt-3 w-full rounded-xl border border-muted/30 bg-bg p-3"
      />
      {errorKey && <p className="mt-2 text-sm text-danger">{t(errorKey)}</p>}
      <PrimaryButton disabled={busy || !value} onClick={() => onConfirm(new Date(value).toISOString())}>
        {t("sleep.confirm")}
      </PrimaryButton>
    </div>
  );
}

function OpenSession({ session }: { session: SleepSession }) {
  const { t, i18n } = useTranslation();
  const now = useNow();
  const stop = useStopSleep();
  const remove = useDeleteSleep();
  const elapsedMin = Math.max(0, Math.floor((now.getTime() - new Date(session.started_at).getTime()) / 60000));

  const err = stop.error instanceof ApiError ? stop.error : null;
  const needsWakeTime = elapsedMin > FORGOTTEN_STOP_MINUTES || err?.code === "wake_time_required";

  return (
    <Card>
      <p className="text-sm text-muted">{t("sleep.sleeping")}</p>
      <p className="mt-1 text-4xl font-semibold">{formatDuration(t, elapsedMin)}</p>
      <p className="mt-1 text-sm text-muted">{t("sleep.since", { time: formatTime(session.started_at, i18n.language) })}</p>
      {needsWakeTime ? (
        <WakeTimePicker
          busy={stop.isPending}
          errorKey={
            err?.code === "invalid_time"
              ? "sleep.invalidTime"
              : err?.code === "too_long"
                ? "sleep.tooLong"
                : null
          }
          onConfirm={(iso) => stop.mutate(iso)}
        />
      ) : (
        <PrimaryButton disabled={stop.isPending} onClick={() => stop.mutate(undefined)}>
          {t("sleep.stop")}
        </PrimaryButton>
      )}
      {err && !["wake_time_required", "invalid_time", "too_long"].includes(err.code) && (
        <p className="mt-2 text-sm text-danger">{t("common.error")}</p>
      )}
      <button
        type="button"
        disabled={remove.isPending}
        onClick={() => {
          void confirmAction(t("sleep.cancelSessionConfirm")).then((confirmed) => {
            if (confirmed) remove.mutate(session.id);
          });
        }}
        className="mt-3 w-full text-sm text-muted underline disabled:opacity-60"
      >
        {t("sleep.cancelSession")}
      </button>
      {remove.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("common.error")}</p>}
    </Card>
  );
}

function LastSleep({ session, onEdit }: { session: SleepSession; onEdit: () => void }) {
  const { t, i18n } = useTranslation();
  return (
    <div className="border-b border-muted/20 pb-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted">{t(session.is_nap ? "sleep.nap" : "sleep.lastSleep")}</p>
          <p className="mt-1 text-3xl font-semibold">{formatDuration(t, session.duration_minutes ?? 0)}</p>
          <p className="mt-1 text-sm text-muted">
            {formatTime(session.started_at, i18n.language)} → {formatTime(session.ended_at!, i18n.language)}
          </p>
        </div>
        <button type="button" onClick={onEdit} className="shrink-0 text-sm text-primary">
          {t("sleep.edit")}
        </button>
      </div>
    </div>
  );
}

function toFormValues(session: SleepSession): SleepFormValues {
  return {
    started_at: session.started_at,
    ended_at: session.ended_at ?? session.started_at,
  };
}

export function SleepCard() {
  const { t } = useTranslation();
  const current = useCurrentSleep();
  const list = useSleepList(5);
  const start = useStartSleep();
  const create = useCreateSleep();
  const update = useUpdateSleep();
  const [mode, setMode] = useState<"none" | "create" | "edit">("none");

  if (current.isPending) return <Skeleton />;
  if (current.isError) return <QueryError error={current.error} retry={() => void current.refetch()} />;
  if (current.data) return <OpenSession session={current.data} />;

  const last = list.data?.find((session) => session.ended_at !== null);
  const editing = mode === "edit" && last !== undefined;

  function save(values: SleepFormValues) {
    if (editing && last) {
      update.mutate({ id: last.id, ...values }, { onSuccess: () => setMode("none") });
    } else {
      create.mutate(values, { onSuccess: () => setMode("none") });
    }
  }

  return (
    <Card>
      {last ? (
        <LastSleep session={last} onEdit={() => setMode(mode === "edit" ? "none" : "edit")} />
      ) : (
        <p className="text-muted">{t("sleep.noData")}</p>
      )}

      {mode !== "none" && (
        <SleepForm
          title={editing ? t("sleep.formEditTitle") : t("sleep.formTitle")}
          initial={editing && last ? toFormValues(last) : undefined}
          busy={create.isPending || update.isPending}
          error={editing ? update.error : create.error}
          onSubmit={save}
          onCancel={() => setMode("none")}
        />
      )}

      {mode === "none" && (
        <>
          <PrimaryButton disabled={start.isPending} onClick={() => start.mutate()}>
            {t("sleep.start")}
          </PrimaryButton>
          <SecondaryButton disabled={create.isPending} onClick={() => setMode("create")}>
            {t("sleep.add")}
          </SecondaryButton>
          {start.isError && <p className="mt-2 text-sm text-danger">{t("common.error")}</p>}
        </>
      )}
    </Card>
  );
}
